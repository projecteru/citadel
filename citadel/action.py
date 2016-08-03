# -*- coding: utf-8 -*-

import json
import logging
from Queue import Queue, Empty
from threading import Thread

import yaml
from grpc.framework.interfaces.face import face
from more_itertools import peekable

from citadel.ext import core
from citadel.libs.json import JSONEncoder
from citadel.libs.utils import with_appcontext
from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.gitlab import get_project_name, get_file_content
from citadel.publish import publisher
from citadel.models.loadbalance import update_elb_for_container


_eof = object()
_log = logging.getLogger(__name__)


class ActionError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message


def action_stream(q):
    """因为grpc这边需要一直同步等待返回, 所以没办法啊, 只好用一个Thread来做这个事情了.
    q就是对应的queue. 需要返回结果的话就用这个来取就行.
    为什么要用Thread呢, 因为Greenlet会死... grpc好渣
    """
    while True:
        try:
            e = q.get(timeout=120)
            if e is _eof:
                break
            yield e
        except Empty:
            break


def _peek_grpc(call):
    """peek一下stream的返回, 不next一次他是不会raise exception的"""
    try:
        ms = peekable(call)
        ms.peek()
    except (face.RemoteError, face.RemoteShutdownError) as e:
        raise ActionError(400, e.details)
    except face.AbortionError as e:
        raise ActionError(500, 'gRPC remote server not available')
    return ms


def build_image(repo, sha, uid='', artifact=''):
    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        raise ActionError(400, 'repo %s does not have app.yaml in root directory' % repo)

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    app = App.get_by_name(appname)
    if not app:
        raise ActionError(400, 'repo %s does not have the right appname in app.yaml' % repo)

    uid = uid or app.id
    ms = _peek_grpc(core.build_image(repo, sha, str(uid), artifact))
    q = Queue()

    @with_appcontext
    def _stream_producer():
        image = ''
        for m in ms:
            if m.status == 'finished':
                image = m.progress
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')
        q.put(_eof)

        release = Release.get_by_app_and_sha(appname, sha)
        if release and image:
            release.update_image(image)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q


def create_container(repo, sha, podname, nodename, entrypoint, cpu, count, networks, envname, extra_env, raw=False):
    pod = core.get_pod(podname)
    if not pod:
        raise ActionError(400, 'pod %s not exist' % podname)

    if nodename:
        node = core.get_node(podname, nodename)
        if not node:
            raise ActionError(400, 'node %s, %s not exist' % (podname, nodename))

    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        raise ActionError(400, 'repo %s, %s does not have app.yaml in root directory' % (repo, sha))

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        raise ActionError(400, 'repo %s, %s does not have the right appname in app.yaml' % (repo, sha))

    # 找不到对应env就算了
    # 需要加一下额外的env
    env = Environment.get_by_app_and_env(appname, envname)
    env = env and env.to_env_vars() or []
    env.extend(extra_env)

    # 如果是raw模式, 用app.yaml里写的base替代
    image = release.image
    if raw:
        image = specs.get('base', '')
    if not image:
        _log.error('repo %s, %s has no image, may not been built yet', repo, sha)
        raise ActionError(400, 'repo %s, %s has no image, may not been built yet' % (repo, sha))

    ms = _peek_grpc(core.create_container(content, appname, image, podname, nodename, entrypoint, cpu, count, networks, env, raw))
    q = Queue()

    @with_appcontext
    def _stream_producer():
        release = Release.get_by_app_and_sha(appname, sha)
        if not release:
            q.put(_eof)
            return

        for m in ms:
            if m.success:
                container = Container.create(release.app.name, release.sha, m.id,
                                             entrypoint, envname, cpu, m.podname, m.nodename)
                publisher.add_container(container)
                log.info('Container [%s] created', m.id)
                update_elb_for_container(container)
            # 这里的顺序一定要注意
            # 必须在创建容器完成之后再把消息丢入队列
            # 否则调用者可能会碰到拿到了消息但是没有容器的状况.
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')

        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q


def remove_container(ids):
    # publish backends
    containers = [Container.get_by_container_id(i) for i in ids]
    for container in containers:
        if not container:
            continue
        publisher.remove_container(container)

    ms = _peek_grpc(core.remove_container(ids))
    q = Queue()

    @with_appcontext
    def _stream_producer():
        for m in ms:
            if m.success:
                update_elb_for_container(container)
                Container.delete_by_container_id(m.id)
                log.info('Container [%s] deleted', m.id)
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')
        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q


def upgrade_container(ids, repo, sha):
    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        raise ActionError(400, 'repo %s, %s does not have app.yaml in root directory' % (repo, sha))

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        raise ActionError(400, 'repo %s, %s does not have the right appname in app.yaml' % (repo, sha))

    if not release.image:
        raise ActionError(400, 'repo %s, %s has not been built yet' % (repo, sha))

    # publish backends
    containers = [Container.get_by_container_id(i) for i in ids]
    for container in containers:
        if not container:
            continue
        publisher.remove_container(container)

    ms = _peek_grpc(core.upgrade_container(ids, release.image))
    q = Queue()

    @with_appcontext
    def _stream_producer():
        for m in ms:
            if m.success:
                old = Container.get_by_container_id(m.id)
                if not old:
                    continue

                c = Container.create(old.appname, sha, m.new_id, old.entrypoint,
                                     old.env, old.cpu_quota, old.podname, old.nodename)
                if not c:
                    continue
                publisher.add_container(c)

                old.delete()
                log.info('Container [%s] upgraded to [%s]', m.id, m.new_id)
            # 这里也要注意顺序
            # 不要让外面出现拿到了消息但是数据还没有更新.
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')

        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q
