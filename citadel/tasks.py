# -*- coding: utf-8 -*-
import json

import yaml
from celery import current_app
from celery.result import AsyncResult
from flask import url_for
from grpc.framework.interfaces.face import face
from more_itertools import peekable

from citadel.config import ELB_APP_NAME, TASK_PUBSUB_CHANNEL, BUILD_ZONE
from citadel.ext import rds, hub
from citadel.libs.json import JSONEncoder
from citadel.libs.utils import notbot_sendmsg, logger
from citadel.models import Container, Release
from citadel.models.app import App
from citadel.models.container import ContainerOverrideStatus
from citadel.models.gitlab import get_project_name, get_file_content, get_build_artifact
from citadel.models.loadbalance import update_elb_for_containers, UpdateELBAction, ELBInstance
from citadel.models.oplog import OPType, OPLog
from citadel.rpc import get_core
from citadel.views.helper import make_kibana_url


class ActionError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        # required by
        # http://docs.celeryproject.org/en/latest/userguide/tasks.html#creating-pickleable-exceptions
        super(ActionError, self).__init__(code, message)

    def __str__(self):
        return self.message


def _peek_grpc(call):
    """peek一下stream的返回, 不next一次他是不会raise exception的"""
    try:
        logger.debug('Peek grpc call %s', call)
        ms = peekable(call)
        ms.peek()
        logger.debug('Peek grpc call %s done', call)
    except (face.RemoteError, face.RemoteShutdownError) as e:
        raise ActionError(500, e.details)
    except face.AbortionError as e:
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
        raise ActionError(400, 'repo %s does not have appname in app.yaml' % repo)

    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        raise ActionError(400, 'release %s, %s not found, maybe not registered yet?' % (repo, sha))
    if release.raw:
        release.update_image(release.specs.base)
        return

    # 尝试通过gitlab_build_id去取最近成功的一次artifact
    if not artifact:
        artifact = get_build_artifact(project_name, sha, gitlab_build_id)

    app = App.get_by_name(appname)
    uid = str(uid or app.uid)

    image = ''
    task_id = self.request.id
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id) if task_id else None
    ms = _peek_grpc(get_core(BUILD_ZONE).build_image(repo, sha, uid, artifact))
    for m in ms:
        rds.publish(channel_name, json.dumps(m, cls=JSONEncoder) + '\n')
        if m.status == 'finished':
            image = m.progress

    if release and image:
        release.update_image(image)


@current_app.task(bind=True)
def create_container(self, deploy_options=None, sha=None, user_id=None, envname=None):
    appname = deploy_options['appname']
    entrypoint = deploy_options['entrypoint']
    zone = deploy_options.pop('zone')
    ms = _peek_grpc(get_core(zone).create_container(deploy_options))

    release = Release.get_by_app_and_sha(appname, sha)

    containers = []
    task_id = self.request.id
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id) if task_id else None
    good_news = []
    bad_news = []
    res = []
    for m in ms:
        content = json.dumps(m, cls=JSONEncoder)
        rds.publish(channel_name, content + '\n')
        res.append(m.to_dict())

        if m.success:
            good_news.append(content)
            logger.debug('Creating %s:%s got grpc message %s', appname, entrypoint, m)
            override_status = ContainerOverrideStatus.DEBUG if deploy_options.get('debug', False) else ContainerOverrideStatus.NONE
            container = Container.create(appname, sha, m.id, entrypoint, envname, deploy_options['cpu_quota'], zone, m.podname, m.nodename, override_status=override_status)
            logger.debug('Container [%s] created', m.id)
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
            bad_news.append(content)

    subscribers = release.specs.subscribers
    msg = 'Deploy {}\n*GOOD NEWS*:\n```{}```'.format(release.name, good_news)
    if bad_news:
        msg += '\n*BAD NEWS*:\n```{}```'.format(bad_news)
        subscribers += ';#platform'
        msg += '\n@timfeirg'

    notbot_sendmsg(subscribers, msg)
    return res


@current_app.task(bind=True)
def create_elb_instance_upon_containers(self, container_ids, name, sha, comment=None, user_id=None):
    if isinstance(container_ids, basestring):
        container_ids = container_ids,

    release = Release.get_by_app_and_sha(ELB_APP_NAME, sha)
    for container_id in container_ids:
        container = Container.get_by_container_id(container_id)
        if not container:
            continue

        ips = container.get_ips()
        ELBInstance.create(ips[0], container.container_id, name, comment)

        # 记录oplog
        op_content = {'elbname': name, 'container_id': container.container_id}
        OPLog.create(user_id, OPType.CREATE_ELB_INSTANCE, release.app.name, release.sha, op_content)


@current_app.task(bind=True)
def remove_container(self, ids, user_id=None):
    if isinstance(ids, basestring):
        ids = [ids]

    containers = [Container.get_by_container_id(i) for i in ids]
    containers = [c for c in containers if c]
    if not containers:
        return
    full_ids = [c.container_id for c in containers]
    zones = set(c.zone for c in containers)
    if len(zones) != 1:
        raise ActionError(400, 'Cannot remove containers across zone')
    zone = zones.pop()

    for c in containers:
        c.mark_removing()

    update_elb_for_containers(containers, UpdateELBAction.REMOVE)

    task_id = self.request.id
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id) if task_id else None
    ms = _peek_grpc(get_core(zone).remove_container(full_ids))
    res = []
    for m in ms:
        rds.publish(channel_name, json.dumps(m, cls=JSONEncoder) + '\n')
        res.append(m.to_dict())

        container = Container.get_by_container_id(m.id)
        if not container:
            logger.info('Container [%s] not found when deleting', m.id)
            continue

        if m.success:
            container.delete()
            # 记录oplog
            op_content = {'container_id': m.id}
            OPLog.create(user_id, OPType.REMOVE_CONTAINER, container.appname, container.sha, op_content)
            logger.debug('Container [%s] deleted', m.id)
        elif 'Key not found' in m.message or 'No such container' in m.message:
            container.delete()
        elif 'Container ID must be length of' in m.message:
            # TODO: this requires core doesn't change this error message,
            # maybe use error code in the future
            continue
        else:
            logger.error('Remove container %s got error: %s', m.id, m.message)
            notbot_sendmsg('#platform', 'Error removing container {}: {}\n@timfeirg'.format(m.id, m.message))

    return res


@current_app.task(bind=True)
def upgrade_container(self, old_container_id, sha, user_id=None):
    """this task will not be called synchronously, thus do not return anything"""
    old_container = Container.get_by_container_id(old_container_id)
    release = old_container.app.get_release(sha)
    if not release or not release.image:
        raise ActionError(400, 'Release %s not found or not built' % sha)

    deploy_options = old_container.deploy_options
    # update image, and use random node
    deploy_options.update({'image': release.image, 'nodename': ''})
    task_id = self.request.id
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id)
    grpc_message = create_container(deploy_options,
                                    sha=release.sha,
                                    user_id=user_id,
                                    envname='SAME')[0]
    rds.publish(channel_name, json.dumps(grpc_message, cls=JSONEncoder) + '\n')

    new_container_id = grpc_message['id']
    new_container = Container.get_by_container_id(new_container_id)
    rds.publish(channel_name, make_sentence_json('Wait for container {} to erect...'.format(new_container.short_id)))
    healthy = new_container.wait_for_erection(timeout=release.erection_timeout)
    # TODO: leave the options to users, let them choose what to do next (wait or rollback)
    if healthy:
        rds.publish(channel_name, make_sentence_json('New container {} OK, remove old container {}'.format(new_container_id, old_container_id)))
        remove_container(old_container_id)
    else:
        rds.publish(channel_name, make_sentence_json('New container {} SO SICK, have to remove...'.format(new_container_id)))
        remove_container(new_container_id)


@current_app.task(bind=True)
def clean_images(self):
    hub_eru_apps = [n for n in hub.get_all_repos() if n.startswith('eruapp')]
    for repo_name in hub_eru_apps:
        appname = repo_name.split('/', 1)[-1]
        for short_sha in hub.get_tags(repo_name) or []:
            if not Release.get_by_app_and_sha(appname, short_sha):
                logger.debug('Delete image %s:%s', appname, short_sha)
                hub.delete_repo(repo_name, short_sha)


@current_app.task(bind=True)
def deal_with_agent_etcd_change(self, key, data):
    container_id = data.get('ID')
    healthy = data.get('Healthy')
    alive = data.get('Alive')
    appname = data.get('Name')
    if None in [container_id, healthy, alive, appname]:
        return
    container = Container.get_by_container_id(container_id)
    if not container:
        return

    msg = ''

    release = Release.get_by_app_and_sha(container.appname, container.sha)
    subscribers = release.specs.subscribers or '#platform'
    if not alive:
        logger.info('[%s, %s, %s] REMOVE [%s] from ELB', container.appname, container.podname, container.entrypoint, container_id)
        update_elb_for_containers(container, UpdateELBAction.REMOVE)
        if not container.is_removing():
            msg = 'Dead container `{}` removed from ELB\ncitadel url: {}\ncontainer log: {}'.format(
                container.short_id,
                url_for('app.app', name=appname, _external=True),
                make_kibana_url(appname=appname, ident=container.ident),
            )

        notbot_sendmsg(subscribers, msg)
        return

    if healthy:
        container.mark_initialized()
        update_elb_for_containers(container)
        logger.debug('[%s, %s, %s] ADD [%s] [%s]', container.appname, container.podname, container.entrypoint, container_id, ','.join(container.get_backends()))
    else:
        update_elb_for_containers(container, UpdateELBAction.REMOVE)
        logger.debug('[%s, %s, %s] DEL [%s] [%s]', container.appname, container.podname, container.entrypoint, container_id, ','.join(container.get_backends()))
        if container.initialized and not container.is_removing():
            msg = 'Sick container `{}` removed from ELB\ncitadel url: {}\ncontainer log: {}'.format(
                container.short_id,
                url_for('app.app', name=appname, _external=True),
                make_kibana_url(appname=appname, ident=container.ident)
            )
        else:
            container.mark_initialized()


def celery_task_stream_response(celery_task_ids):
    if isinstance(celery_task_ids, basestring):
        celery_task_ids = celery_task_ids,

    task_progress_channels = [TASK_PUBSUB_CHANNEL.format(task_id=id_) for id_ in celery_task_ids]
    pubsub = rds.pubsub()
    pubsub.subscribe(task_progress_channels)
    for item in pubsub.listen():
        logger.debug('Got pubsub message: %s', item)
        # each content is a single JSON encoded grpc message
        content = item['data']
        # omit the initial message where item['data'] is 1L
        if not isinstance(content, basestring):
            continue
        # task will publish TASK_PUBSUB_EOF at success or failure
        if content.startswith('CELERY_TASK_DONE'):
            finished_task_id = content[content.find(':') + 1:]
            finished_task_channel = TASK_PUBSUB_CHANNEL.format(task_id=finished_task_id)
            logger.debug('Task {} finished, break celery_task_stream_response'.format(finished_task_id))
            pubsub.unsubscribe(finished_task_channel)
        else:
            yield content


def celery_task_stream_traceback(celery_task_ids):
    """collect traceback for celery tasks, do not guarantee send order"""
    if isinstance(celery_task_ids, basestring):
        celery_task_ids = celery_task_ids,

    for task_id in celery_task_ids:
        async_result = AsyncResult(task_id)
        async_result.wait(timeout=120, propagate=False)
        if async_result.failed():
            yield json.dumps({'success': False, 'error': async_result.traceback})


def make_sentence_json(message):
    msg = json.dumps({'type': 'sentence', 'message': message}, cls=JSONEncoder)
    return msg + '\n'
