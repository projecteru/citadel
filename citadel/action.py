# -*- coding: utf-8 -*-

import json
import logging
from Queue import Queue, Empty
from threading import Thread

import yaml
from flask import g
from grpc.framework.interfaces.face import face
from more_itertools import peekable

from citadel.ext import core
from citadel.libs.json import JSONEncoder
from citadel.libs.utils import with_appcontext
from citadel.publish import publisher

from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.gitlab import get_project_name, get_file_content
from citadel.models.loadbalance import update_elb_for_containers
from citadel.models.oplog import OPType, OPLog


_eof = object()
_log = logging.getLogger(__name__)


class ActionError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message


def _get_current_user_id():
    """with_appcontext的线程是没有g.user的, 得通过其他方式拿到了之后传进去."""
    if not hasattr(g, 'user'):
        return 0
    return g.user and g.user.id or 0


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


def create_container(repo, sha, podname, nodename, entrypoint, cpu, memory, count, networks, envname, extra_env, raw=False):
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

    ms = _peek_grpc(core.create_container(content, appname, image, podname, nodename, entrypoint, cpu, memory, count, networks, env, raw))
    q = Queue()

    user_id = _get_current_user_id()

    @with_appcontext
    def _stream_producer():
        release = Release.get_by_app_and_sha(appname, sha)
        if not release:
            q.put(_eof)
            return

        containers = []
        for m in ms:
            if m.success:
                container = Container.create(release.app.name, release.sha, m.id,
                                             entrypoint, envname, cpu, m.podname, m.nodename)
                if not container:
                    _log.error('Create [%s] created failed', m.id)
                    continue

                # 记录oplog, cpu这里需要处理下, 因为返回的消息里也有这个值
                op_content = {'entrypoint': entrypoint, 'envname': envname, 'networks': networks}
                op_content.update(m.to_dict())
                op_content['cpu'] = cpu
                OPLog.create(user_id, OPType.CREATE_CONTAINER, appname, release.sha, op_content)

                containers.append(container)
                publisher.add_container(container)
                _log.info('Container [%s] created', m.id)
            # 这里的顺序一定要注意
            # 必须在创建容器完成之后再把消息丢入队列
            # 否则调用者可能会碰到拿到了消息但是没有容器的状况.
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')

        update_elb_for_containers(containers)
        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q


def remove_container(ids):
    # publish backends
    containers = [Container.get_by_container_id(i) for i in ids]
    for c in containers:
        if not c:
            continue
        publisher.remove_container(c)

    # TODO: handle the situations where core try-and-fail to delete container
    update_elb_for_containers(containers)
    ms = _peek_grpc(core.remove_container(ids))
    q = Queue()

    user_id = _get_current_user_id()

    @with_appcontext
    def _stream_producer():
        for m in ms:
            if m.success:
                container = Container.get_by_container_id(m.id)
                if not container:
                    _log.info('Container [%s] not found when deleting', m.id)
                    continue

                # 记录oplog
                op_content = {'container_id': m.id}
                OPLog.create(user_id, OPType.REMOVE_CONTAINER, container.appname, container.sha, op_content)

                container.delete()

                _log.info('Container [%s] deleted', m.id)
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')
        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q


def upgrade_container(ids, repo, sha):
    containers = [Container.get_by_container_id(i) for i in ids]
    containers = [c for c in containers if c and c.sha != sha]
    if not containers:
        raise ActionError(400, 'No containers to upgrade')

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
    for container in containers:
        if not container:
            continue
        publisher.remove_container(container)

    ms = _peek_grpc(core.upgrade_container(ids, release.image))
    q = Queue()

    user_id = _get_current_user_id()

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

                # 记录oplog
                op_content = {'old_id': m.id, 'new_id': m.new_id, 'old_sha': old.sha, 'new_sha': c.sha}
                OPLog.create(user_id, OPType.UPGRADE_CONTAINER, c.appname, c.sha, op_content)

                publisher.add_container(c)
                # 这里只能一个一个更新 elb 了，无法批量更新
                update_elb_for_containers(c)
                old.delete()

                _log.info('Container [%s] upgraded to [%s]', m.id, m.new_id)
            # 这里也要注意顺序
            # 不要让外面出现拿到了消息但是数据还没有更新.
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')

        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return q
