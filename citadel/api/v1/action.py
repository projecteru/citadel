# coding: utf-8

import json
import yaml
from more_itertools import peekable
from flask import abort, request, Response
from threading import Thread
from Queue import Queue, Empty
from grpc.framework.interfaces.face import face

from citadel.ext import core
from citadel.publish import publisher
from citadel.libs.json import JSONEncoder
from citadel.libs.view import create_api_blueprint
from citadel.libs.datastructure import AbortDict
from citadel.libs.utils import with_appcontext

from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.gitlab import get_project_name, get_file_content
from citadel.models.env import Environment


# 把action都挂在/api/:version/下, 不再加前缀
# 也不需要他帮忙自动转JSON了
bp = create_api_blueprint('action', __name__, jsonize=False)


_eof = object()


def _stream_consumer(q):
    """
    因为grpc这边需要一直同步等待返回,
    所以没办法啊, 只好用一个Thread来做这个事情了.
    q就是对应的queue.
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
        abort(400, e.details)
    except face.AbortionError as e:
        abort(500, 'gRPC remote server not available')
    return ms


@bp.route('/build', methods=['POST'])
def build():
    """
    可以这么玩玩:
    $ http --stream POST localhost:5000/api/v1/build repo=git@gitlab.ricebook.net:tonic/ci-test.git sha=1d74377e99dcfb3fd892f9eaeab91e1e229179ba uid=4401
    """
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    repo = data['repo']
    sha = data['sha']
    artifact = data.get('artifact', '')

    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        abort(400, 'repo %s does not have app.yaml in root directory' % repo)

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    app = App.get_by_name(appname)
    if not app:
        abort(400, 'repo %s does not have the right appname in app.yaml' % repo)

    uid = data.get('uid', None) or app.id
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

    return Response(_stream_consumer(q), mimetype='application/json')


@bp.route('/deploy', methods=['POST'])
def deploy():
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    repo = data['repo']
    sha = data['sha']
    podname = data['podname']
    entrypoint = data['entrypoint']
    cpu = float(data['cpu_quota'])
    count = int(data['count'])
    networks = data.get('networks', {})
    envname = data.get('env', '')

    pod = core.get_pod(podname)
    if not pod:
        abort(400, 'pod %s not exist' % podname)

    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        abort(400, 'repo %s, %s does not have app.yaml in root directory' % (repo, sha))

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(400, 'repo %s, %s does not have the right appname in app.yaml' % (repo, sha))

    if not release.image:
        abort(400, 'repo %s, %s has not been built yet' % (repo, sha))

    # 找不到对应env就算了
    # 需要加一下额外的env
    env = Environment.get_by_app_and_env(appname, envname)
    env = env and env.to_env_vars() or []
    env.extend(data.get('extra_env', []))

    image = release.image
    ms = _peek_grpc(core.create_container(content, appname, image, podname, entrypoint, cpu, count, networks, env))
    q = Queue()

    @with_appcontext
    def _stream_producer():
        release = Release.get_by_app_and_sha(appname, sha)
        if not release:
            q.put(_eof)
            return

        for m in ms:
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')
            if not m.success:
                continue

            container = Container.create(release.app.name, release.sha, m.id,
                                         entrypoint, 'env', cpu, m.podname, m.nodename)
            publisher.add_container(container)
        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return Response(_stream_consumer(q), mimetype='application/json')


@bp.route('/remove', methods=['POST'])
def remove_container():
    data = AbortDict(request.get_json())
    ids = data['ids']

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
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')
            if not m.success:
                continue

            Container.delete_by_container_id(m.id)
        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return Response(_stream_consumer(q), mimetype='application/json')


@bp.route('/upgrade', methods=['POST'])
def upgrade_container():
    data = AbortDict(request.get_json())
    ids = data['ids']
    repo = data['repo']
    sha = data['sha']

    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        abort(400, 'repo %s, %s does not have app.yaml in root directory' % (repo, sha))

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(400, 'repo %s, %s does not have the right appname in app.yaml' % (repo, sha))

    if not release.image:
        abort(400, 'repo %s, %s has not been built yet' % (repo, sha))

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
            q.put(json.dumps(m, cls=JSONEncoder) + '\n')
            if not m.success:
                continue

            old = Container.get_by_container_id(m.id)
            if not old:
                continue

            c = Container.create(old.appname, sha, m.new_id, old.entrypoint,
                                 old.env, old.cpu_quota, old.podname, old.nodename)
            if not c:
                continue
            publisher.add_container(c)

            old.delete()

        q.put(_eof)

    t = Thread(target=_stream_producer)
    t.daemon = True
    t.start()

    return Response(_stream_consumer(q), mimetype='application/json')
