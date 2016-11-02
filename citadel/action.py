# -*- coding: utf-8 -*-

import json
from Queue import Queue, Empty

import yaml
from flask import g
from grpc.framework.interfaces.face import face
from more_itertools import peekable

from citadel.libs.json import JSONEncoder
from citadel.libs.utils import logger, ContextThread
from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.gitlab import get_project_name, get_file_content, get_build_artifact
from citadel.models.loadbalance import update_elb_for_containers, UpdateELBAction
from citadel.models.oplog import OPType, OPLog
from citadel.publish import publisher
from citadel.rpc import core


_eof = object()


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


def _peek_grpc(call, thread_queue=None):
    """peek一下stream的返回, 不next一次他是不会raise exception的,
    如果是在thread里call，出错的时候还要把eof写进queue里"""
    try:
        ms = peekable(call)
        ms.peek()
    except (face.RemoteError, face.RemoteShutdownError) as e:
        if thread_queue:
            thread_queue.put(_eof)

        raise ActionError(400, e.details)
    except face.AbortionError as e:
        if thread_queue:
            thread_queue.put(_eof)

        raise ActionError(500, 'gRPC remote server not available')
    return ms


class BuildThread(ContextThread):

    def __init__(self, q, repo, sha, uid='', artifact='', gitlab_build_id=''):
        logger.debug('Initialize BuildThread for %s:%s, uid %s, artifact %s, gitlab_build_id %s', repo, sha, uid, artifact, gitlab_build_id)
        super(BuildThread, self).__init__()
        self.daemon = True
        self.q = q

        project_name = get_project_name(repo)
        specs_text = get_file_content(project_name, 'app.yaml', sha)
        if not specs_text:
            raise ActionError(400, 'repo %s does not have app.yaml in root directory' % repo)

        specs = yaml.load(specs_text)
        appname = specs.get('appname', '')
        if not appname:
            raise ActionError(400, 'repo %s does not have the right appname in app.yaml' % repo)

        # 尝试通过gitlab_build_id去取最近成功的一次artifact
        if not artifact:
            artifact = get_build_artifact(project_name, sha, gitlab_build_id)

        app = App.get_by_name(appname)
        uid = uid or app.uid

        self.appname = appname
        self.repo = repo
        self.sha = sha
        self.uid = str(uid)
        self.artifact = artifact

    def execute(self):
        logger.debug('Building in thread, repo %s:%s, uid %s, artifact %s', self.repo, self.sha, self.uid, self.artifact)
        image = ''
        ms = _peek_grpc(core.build_image(self.repo, self.sha, self.uid, self.artifact), thread_queue=self.q)
        for m in ms:
            if m.status == 'finished':
                image = m.progress
            self.q.put(json.dumps(m, cls=JSONEncoder) + '\n')
        self.q.put(_eof)

        release = Release.get_by_app_and_sha(self.appname, self.sha)
        if release and image:
            release.update_image(image)


def build_image(repo, sha, uid='', artifact='', gitlab_build_id=''):
    q = Queue()
    t = BuildThread(q, repo, sha, uid=uid, artifact=artifact, gitlab_build_id=gitlab_build_id)
    t.start()
    return q


class CreateContainerThread(ContextThread):

    def __init__(self, q, repo, sha, podname, nodename, entrypoint, cpu, memory, count, networks, envname, extra_env=(), raw=False, extra_args='', debug=False):
        super(CreateContainerThread, self).__init__()
        self.daemon = True

        pod = core.get_pod(podname)
        if not pod:
            raise ActionError(400, 'pod %s not exist' % podname)

        if nodename:
            node = core.get_node(podname, nodename)
            if not node:
                raise ActionError(400, 'node %s, %s not exist' % (podname, nodename))

        project_name = get_project_name(repo)
        specs_text = get_file_content(project_name, 'app.yaml', sha)
        if not specs_text:
            raise ActionError(400, 'repo %s, %s does not have app.yaml in root directory' % (repo, sha))

        specs = yaml.load(specs_text)
        appname = specs.get('appname', '')
        release = Release.get_by_app_and_sha(appname, sha)
        if not release:
            raise ActionError(400, 'repo %s, %s does not have the right appname in app.yaml' % (repo, sha))

        # 如果是raw模式, 用app.yaml里写的base替代
        image = release.image
        if raw:
            image = specs.get('base', '')
        if not image:
            logger.error('repo %s, %s has no image, may not been built yet', repo, sha)
            raise ActionError(400, 'repo %s, %s has no image, may not been built yet' % (repo, sha))

        # 找不到对应env就算了
        # 需要加一下额外的env
        env = Environment.get_by_app_and_env(appname, envname)
        env = env and env.to_env_vars() or []
        env.extend(extra_env)

        logger.debug('Creating %s:%s container using env %s on pod %s:%s with network %s, cpu %s, memory %s', appname, entrypoint, env, podname, nodename, networks, cpu, memory)

        self.q = q
        self.specs_text = specs_text
        self.appname = appname
        self.image = image
        self.repo = repo
        self.sha = sha
        self.podname = podname
        self.nodename = nodename
        self.entrypoint = entrypoint
        self.cpu = cpu
        self.memory = memory
        self.count = count
        self.networks = networks
        self.envname = envname
        self.env = env
        self.raw = raw
        self.extra_args = extra_args
        self.debug = debug
        self.user_id = _get_current_user_id()

    def execute(self):
        ms = _peek_grpc(core.create_container(self.specs_text, self.appname,
                                              self.image, self.podname,
                                              self.nodename, self.entrypoint,
                                              self.cpu, self.memory,
                                              self.count, self.networks,
                                              self.env, raw=self.raw,
                                              extra_args=self.extra_args, debug=self.debug),
                        thread_queue=self.q)

        release = Release.get_by_app_and_sha(self.appname, self.sha)
        if not release:
            self.q.put(_eof)
            return

        containers = []
        for m in ms:
            if m.success:
                logger.debug('Creating %s:%s container Got grpc message %s', self.appname, self.entrypoint, m)
                container = Container.create(release.app.name, release.sha, m.id,
                                             self.entrypoint, self.envname, self.cpu, m.podname, m.nodename)
                if not container:
                    logger.error('Create [%s] created failed', m.id)
                    continue

                # 记录oplog, cpu这里需要处理下, 因为返回的消息里也有这个值
                op_content = {'entrypoint': self.entrypoint, 'envname': self.envname, 'networks': self.networks}
                op_content.update(m.to_dict())
                op_content['cpu'] = self.cpu
                OPLog.create(self.user_id, OPType.CREATE_CONTAINER, self.appname, release.sha, op_content)

                containers.append(container)
                publisher.add_container(container)
                logger.info('Container [%s] created', m.id)
            # 这里的顺序一定要注意
            # 必须在创建容器完成之后再把消息丢入队列
            # 否则调用者可能会碰到拿到了消息但是没有容器的状况.
            self.q.put(json.dumps(m, cls=JSONEncoder) + '\n')

        update_elb_for_containers(containers)
        self.q.put(_eof)


def create_container(repo, sha, podname, nodename, entrypoint, cpu, memory, count, networks, envname, extra_env=(), raw=False, extra_args='', debug=False):
    q = Queue()
    t = CreateContainerThread(q, repo, sha, podname, nodename, entrypoint, cpu, memory, count, networks, envname, extra_env=extra_env, raw=raw, extra_args=extra_args, debug=debug)
    t.start()
    return q


class RemoveContainerThread(ContextThread):

    def __init__(self, q, ids):
        super(RemoveContainerThread, self).__init__()
        self.daemon = True

        # publish backends
        containers = [Container.get_by_container_id(i) for i in ids]
        containers = [c for c in containers if c]
        for c in containers:
            c.mark_removing()
            publisher.remove_container(c)

        # TODO: handle the situations where core try-and-fail to delete container
        update_elb_for_containers(containers, UpdateELBAction.REMOVE)

        self.q = q
        self.ids = ids
        self.user_id = _get_current_user_id()

    def execute(self):
        ms = _peek_grpc(core.remove_container(self.ids), thread_queue=self.q)
        for m in ms:
            container = Container.get_by_container_id(m.id)
            if not container:
                logger.info('Container [%s] not found when deleting', m.id)
                continue

            if m.success:
                # 记录oplog
                op_content = {'container_id': m.id}
                OPLog.create(self.user_id, OPType.REMOVE_CONTAINER, container.appname, container.sha, op_content)
                logger.info('Container [%s] deleted', m.id)
            else:
                logger.info('Container [%s] error, but still deleted', m.id)
            container.delete()
            self.q.put(json.dumps(m, cls=JSONEncoder) + '\n')
        self.q.put(_eof)


def remove_container(ids):
    q = Queue()
    t = RemoveContainerThread(q, ids)
    t.start()
    return q


class UpgradeContainerThread(ContextThread):

    def __init__(self, q, ids, repo, sha):
        super(UpgradeContainerThread, self).__init__()
        self.daemon = True
        self.q = q

        if len(sha) != 40:
            raise ActionError(400, 'SHA must be in length 40')

        containers = [Container.get_by_container_id(i) for i in ids]
        containers = [c for c in containers if c and c.sha != sha]
        if not containers:
            raise ActionError(400, 'No containers to upgrade')

        project_name = get_project_name(repo)
        specs_text = get_file_content(project_name, 'app.yaml', sha)
        if not specs_text:
            raise ActionError(400, 'repo %s, %s does not have app.yaml in root directory' % (repo, sha))

        specs = yaml.load(specs_text)
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
            container.mark_removing()
            publisher.remove_container(container)

        self.ids = ids
        self.repo = repo
        self.sha = sha
        self.image = release.image
        self.user_id = _get_current_user_id()

    def execute(self):
        ms = _peek_grpc(core.upgrade_container(self.ids, self.image), thread_queue=self.q)
        for m in ms:
            if m.success:
                old = Container.get_by_container_id(m.id)
                if not old:
                    continue

                c = Container.create(old.appname, self.sha, m.new_id, old.entrypoint,
                                     old.env, old.cpu_quota, old.podname, old.nodename)
                if not c:
                    continue

                # 记录oplog
                op_content = {'old_id': m.id, 'new_id': m.new_id, 'old_sha': old.sha, 'new_sha': c.sha}
                OPLog.create(self.user_id, OPType.UPGRADE_CONTAINER, c.appname, c.sha, op_content)

                publisher.add_container(c)
                # 这里只能一个一个更新 elb 了，无法批量更新
                update_elb_for_containers(old, UpdateELBAction.REMOVE)
                old.delete()

                logger.info('Container [%s] upgraded to [%s]', m.id, m.new_id)
            # 这里也要注意顺序
            # 不要让外面出现拿到了消息但是数据还没有更新.
            self.q.put(json.dumps(m, cls=JSONEncoder) + '\n')

        self.q.put(_eof)


def upgrade_container(ids, repo, sha):
    q = Queue()
    t = UpgradeContainerThread(q, ids, repo, sha)
    t.start()
    return q
