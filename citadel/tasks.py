# -*- coding: utf-8 -*-
import json
from Queue import Empty, Queue

import yaml
from celery import current_app
from flask import g
from grpc.framework.interfaces.face import face
from more_itertools import peekable

from citadel.config import TASK_PUBSUB_CHANNEL, TASK_PUBSUB_EOF
from citadel.ext import rds
from citadel.libs.json import JSONEncoder
from citadel.libs.utils import logger, ContextThread, notbot_sendmsg
from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.gitlab import get_project_name, get_file_content, get_build_artifact
from citadel.models.loadbalance import update_elb_for_containers, UpdateELBAction
from citadel.models.oplog import OPType, OPLog
from citadel.rpc import core


_eof = object()


class ActionError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return self.message


def _peek_grpc(call, thread_queue=None):
    """peek一下stream的返回, 不next一次他是不会raise exception的,
    如果是在thread里call，出错的时候还要把eof写进queue里"""
    try:
        logger.debug('Peek grpc call %s', call)
        ms = peekable(call)
        ms.peek()
        logger.debug('Peek grpc call %s done', call)
    except (face.RemoteError, face.RemoteShutdownError) as e:
        logger.error('gRPC exception: %s', e.details)
        if thread_queue:
            err_msg = {'error': e.details}
            thread_queue.put(json.dumps(err_msg))
            thread_queue.put(_eof)

        # raise ActionError here to terminate queue, but we won't be able to
        # handle this exception
        raise ActionError(500, e.details)
    except face.AbortionError as e:
        logger.error('gRPC exception: %s', e.details)
        if thread_queue:
            err_msg = {'error': e.details}
            thread_queue.put(json.dumps(err_msg))
            thread_queue.put(_eof)

        raise ActionError(500, 'gRPC remote server not available')
    return ms


@current_app.task(bind=True)
def build_image(self, repo, sha, uid='', artifact='', gitlab_build_id=''):
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
    uid = str(uid or app.uid)

    image = ''
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=self.request.id)
    ms = _peek_grpc(core.build_image(repo, sha, uid, artifact))
    for m in ms:
        rds.publish(channel_name, json.dumps(m, cls=JSONEncoder) + '\n')
        if m.status == 'finished':
            image = m.progress

    release = Release.get_by_app_and_sha(appname, sha)
    if release and image:
        release.update_image(image)


@current_app.task(bind=True)
def create_container(self, deploy_options=None, sha=None, user_id=None, envname=None):
    appname = deploy_options['appname']
    entrypoint = deploy_options['entrypoint']
    ms = _peek_grpc(core.create_container(deploy_options))

    release = Release.get_by_app_and_sha(appname, sha)

    containers = []
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=self.request.id)
    good_news = []
    bad_news = []
    for m in ms:
        rds.publish(channel_name, json.dumps(m, cls=JSONEncoder) + '\n')
        if m.success:
            good_news.append(m)
            logger.debug('Creating %s:%s got grpc message %s', appname, entrypoint, m)
            container = Container.create(appname, sha, m.id, entrypoint, envname, deploy_options['cpu_quota'], m.podname, m.nodename)
            logger.info('Container [%s] created', m.id)
            if not container:
                # TODO: can't just continue here, must create container
                logger.error('Create [%s] created failed', m.id)
                continue
            containers.append(container)

            op_content = {'entrypoint': deploy_options['entrypoint'], 'envname': envname, 'networks': deploy_options['networks']}
            op_content.update(m.to_dict())
            op_content['cpu'] = deploy_options['cpu_quota']
            OPLog.create(user_id, OPType.CREATE_CONTAINER, appname, sha, op_content)
        else:
            logger.error('Error when creating container: %s', m.error)
            bad_news.append(m)

    update_elb_for_containers(containers)

    subscribers = release.specs.subscribers
    msg = 'Deploy {}\n*GOOD NEWS*:\n```{}```'.format(release.name, good_news)
    if bad_news:
        msg += '\n*BAD NEWS*:\n```{}```'.format(bad_news)
        subscribers += ';#platform'
        msg += '\n@timfeirg'

    notbot_sendmsg(subscribers, msg)


@current_app.task(bind=True)
def remove_container(self, ids, user_id=None):
    # publish backends
    containers = [Container.get_by_container_id(i) for i in ids]
    containers = [c for c in containers if c]
    full_ids = [c.container_id for c in containers]
    for c in containers:
        c.mark_removing()

    update_elb_for_containers(containers, UpdateELBAction.REMOVE)

    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=self.request.id)
    ms = _peek_grpc(core.remove_container(full_ids))
    for m in ms:
        rds.publish(channel_name, json.dumps(m, cls=JSONEncoder) + '\n')
        container = Container.get_by_container_id(m.id)
        if not container:
            logger.info('Container [%s] not found when deleting', m.id)
            continue

        if m.success:
            # 记录oplog
            op_content = {'container_id': m.id}
            OPLog.create(user_id, OPType.REMOVE_CONTAINER, container.appname, container.sha, op_content)
            logger.info('Container [%s] deleted', m.id)
        elif 'Container ID must be length of' in m.message:
            # TODO: this requires core doesn't change this error message,
            # maybe use error code in the future
            continue
        else:
            logger.info('Container [%s] error, but still deleted', m.id)

        container.delete()


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
            logger.debug('Action stream got message %s', e)
            yield e
        except Empty:
            break


def celery_task_stream_response(celery_task_id):
    task_progress_channel = TASK_PUBSUB_CHANNEL.format(task_id=celery_task_id)
    pubsub = rds.pubsub()
    pubsub.subscribe([task_progress_channel])
    for item in pubsub.listen():
        logger.debug('Got pubsub message: %s', item)
        # each content is a single JSON encoded grpc message
        content = item['data']
        # omit the initial message where item['data'] is 1L
        if not isinstance(content, basestring):
            continue
        # task will publish TASK_PUBSUB_EOF at success or failure
        if content == TASK_PUBSUB_EOF:
            logger.debug('Got EOF from pubsub, break celery_task_stream_response')
            break
        else:
            yield content
