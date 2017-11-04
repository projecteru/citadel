# -*- coding: utf-8 -*-
import json
from celery import current_app
from celery.result import AsyncResult
from datetime import datetime, timedelta
from flask import url_for
from grpc import RpcError, StatusCode
from grpc.framework.interfaces.face import face
from humanfriendly import parse_timespan
from more_itertools import peekable

from citadel.config import ZONE_CONFIG, CITADEL_TACKLE_TASK_THROTTLING_KEY, ELB_APP_NAME, TASK_PUBSUB_CHANNEL, BUILD_ZONE, CITADEL_HEALTH_CHECK_STATS_KEY
from citadel.ext import rds, hub
from citadel.libs.jsonutils import JSONEncoder
from citadel.libs.utils import notbot_sendmsg, logger, make_sentence_json
from citadel.models import Container, Release
from citadel.models.app import App
from citadel.models.base import ModelDeleteError
from citadel.models.container import ContainerOverrideStatus
from citadel.models.loadbalance import update_elb_for_containers, UpdateELBAction, ELBInstance
from citadel.models.oplog import OPType, OPLog
from citadel.rpc import get_core
from citadel.views.helper import make_deploy_options, make_kibana_url


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
        ms = peekable(call)
        ms.peek()
    except (face.RemoteError, face.RemoteShutdownError) as e:
        raise ActionError(500, e.details)
    except face.AbortionError as e:
        raise ActionError(500, 'gRPC remote server not available')
    return ms


@current_app.task(bind=True)
def record_health_status(self):
    """health check for citadel itself:
        if citadel web is down, sa will know
        if citadel worker is down, the health stats in redis will expire in 20 secs, and then sa will know
        if eru-core is down, send slack message
    """
    for zone in ZONE_CONFIG:
        core = get_core(zone)
        try:
            core.list_pods()
        except RpcError as e:
            if e.code() is StatusCode.UNAVAILABLE:
                msg = 'eru-core ({}) is down, @eru will fix this ASAP'.format(zone)
                rds.setex(CITADEL_HEALTH_CHECK_STATS_KEY, msg, 30)
                notbot_sendmsg('#platform', msg)

    rds.setex(CITADEL_HEALTH_CHECK_STATS_KEY, 'OK', 30)


@current_app.task(bind=True)
def build_image(self, appname, repo, sha, uid='', artifact=''):
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        raise ActionError(400, 'release %s, %s not found, maybe not registered yet?' % (repo, sha))
    if release.raw:
        release.update_image(release.specs.base)
        return

    app = App.get_by_name(appname)
    uid = str(uid or app.id)

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
    app = App.get_by_name(appname)
    entrypoint = deploy_options['entrypoint']
    zone = deploy_options.pop('zone')
    ms = _peek_grpc(get_core(zone).create_container(deploy_options))

    task_id = self.request.id
    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id) if task_id else None
    bad_news = []
    res = []
    for m in ms:
        content = json.dumps(m, cls=JSONEncoder)
        rds.publish(channel_name, content + '\n')
        res.append(m.to_dict())

        if m.success:
            logger.debug('Creating container %s:%s got grpc message %s', appname, entrypoint, m)
            override_status = ContainerOverrideStatus.DEBUG if deploy_options.get('debug', False) else ContainerOverrideStatus.NONE
            container = Container.create(appname,
                                         sha,
                                         m.id,
                                         entrypoint,
                                         envname,
                                         deploy_options['cpu_quota'],
                                         deploy_options['memory'],
                                         zone,
                                         m.podname,
                                         m.nodename,
                                         override_status=override_status)

            op_content = {'entrypoint': deploy_options['entrypoint'], 'envname': envname, 'networks': deploy_options['networks']}
            op_content.update(m.to_dict())
            op_content['cpu'] = deploy_options['cpu_quota']
            OPLog.create(user_id,
                         OPType.CREATE_CONTAINER,
                         appname=appname,
                         sha=sha,
                         zone=zone,
                         content=op_content)
        else:
            bad_news.append(content)

    if bad_news:
        msg = 'Deploy {}\n*BAD NEWS*:\n```\n{}\n```\n'.format(appname, bad_news)
        notbot_sendmsg(app.subscribers, msg)

    return res


@current_app.task(bind=True)
def create_elb_instance_upon_containers(self, container_ids, name, sha, comment=None, user_id=None):
    if isinstance(container_ids, str):
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
        OPLog.create(user_id,
                     OPType.CREATE_ELB_INSTANCE,
                     appname=release.app.name,
                     sha=release.sha,
                     zone=container.zone,
                     content=op_content)


@current_app.task(bind=True)
def remove_container(self, ids, user_id=None):
    if isinstance(ids, str):
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
            OPLog.create(user_id,
                         OPType.REMOVE_CONTAINER,
                         appname=container.appname,
                         sha=container.sha,
                         zone=container.zone,
                         content=op_content)
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
def upgrade_container_dispatch(self, container_id, sha, user_id=None):
    container = Container.get_by_container_id(container_id)
    release = container.app.get_release(sha)
    if not release or not release.image:
        raise ActionError(400, 'Release %s not found or not built' % sha)

    deploy_options = container.deploy_options
    deploy_options['image'], _ = release.describe_entrypoint_image(container.entrypoint)
    if not release.specs.freeze_node:
        deploy_options['nodename'] = ''

    channel_name = TASK_PUBSUB_CHANNEL.format(task_id=self.request.id)
    rds.publish(channel_name, make_sentence_json('Upgrading container using options {}'.format(deploy_options)))

    if release.smooth_upgrade:
        smooth_upgrade_container(container_id,
                                 sha,
                                 deploy_options,
                                 channel_name,
                                 user_id=user_id)
    else:
        upgrade_container(container_id,
                          sha,
                          deploy_options,
                          channel_name,
                          user_id=user_id)


def upgrade_container(container_id, sha, deploy_options, channel_name, user_id=None):
    """Remove old container, and then start new one only after the old one's removed"""
    rds.publish(channel_name, make_sentence_json('Removing old container {} ...'.format(container_id)))
    remove_container(container_id, user_id=user_id)

    rds.publish(channel_name, make_sentence_json('Starting new container to replace {} ...'.format(container_id)))
    grpc_message = create_container(deploy_options,
                                    sha=sha,
                                    user_id=user_id,
                                    envname='SAME')[0]
    new_container_id = grpc_message['id']
    rds.publish(channel_name, make_sentence_json('New container created: {}'.format(new_container_id)))


def smooth_upgrade_container(container_id, sha, deploy_options, channel_name, user_id=None):
    """Start new container, wait for it to become healthy, then remove the old one"""
    container = Container.get_by_container_id(container_id)
    rds.publish(channel_name, make_sentence_json('Starting new container to replace {} ...'.format(container_id)))
    grpc_message = create_container(deploy_options,
                                    sha=sha,
                                    user_id=user_id,
                                    envname='SAME')[0]
    rds.publish(channel_name, json.dumps(grpc_message, cls=JSONEncoder) + '\n')
    if not grpc_message['success']:
        rds.publish(channel_name, make_sentence_json('Create new container for {} failed'.format(container)))
        return

    new_container_id = grpc_message['id']
    new_container = Container.get_by_container_id(new_container_id)
    rds.publish(channel_name, make_sentence_json('Wait for new container {} to erect...'.format(new_container)))
    healthy = new_container.wait_for_erection(new_container.release.erection_timeout)
    if healthy:
        rds.publish(channel_name, make_sentence_json('New container {} OK, remove old container {}'.format(new_container_id, container_id)))
        remove_container(container_id, user_id=user_id)
    else:
        rds.publish(channel_name, make_sentence_json('New container {} still sick, have to remove ...'.format(new_container_id)))
        remove_container(new_container_id, user_id=user_id)


@current_app.task(bind=True)
def clean_stuff(self):
    # clean unused releases
    now = datetime.now()
    window = now - timedelta(days=30), now
    last_week_oplogs = OPLog.get_by(time_window=window)
    last_week_sha = set(oplog.sha for oplog in last_week_oplogs if oplog.sha)
    for r in Release.query.filter(Release.created<now - timedelta(days=30)).all():
        if r.sha in last_week_sha:
            continue
        try:
            r.delete()
        except ModelDeleteError:
            continue

    # clean detached images
    hub_eru_apps = [n for n in hub.get_all_repos() if n.startswith('eruapp')]
    for repo_name in hub_eru_apps:
        appname = repo_name.split('/', 1)[-1]
        for short_sha in hub.get_tags(repo_name) or []:
            if not Release.get_by_app_and_sha(appname, short_sha):
                if hub.delete_repo(repo_name, short_sha):
                    logger.info('Delete image %s:%s', appname, short_sha)

    # clean oplogs
    threshold = datetime.now() - timedelta(days=7)
    OPLog.query.filter(OPLog.created < threshold).delete()


@current_app.task(bind=True)
def deal_with_agent_etcd_change(self, key, data):
    container_id = data.get('ID')
    healthy = data.get('Healthy')
    alive = data.get('Alive')
    appname = data.get('Name')
    app = App.get_by_name(appname)
    container = Container.get_by_container_id(container_id)
    if None in [container_id, healthy, alive, appname, app, container]:
        return

    subscribers = app.subscribers
    msg = ''

    if not alive:
        logger.info('[%s, %s, %s] REMOVE [%s] from ELB', container.appname, container.podname, container.entrypoint, container_id)
        update_elb_for_containers(container, UpdateELBAction.REMOVE)

        exitcode = container.info.get('State', {}).get('ExitCode', None)
        # remove cronjob container
        if exitcode == 0 and container.is_cronjob():
            remove_container(container_id)
            return

        if not container.is_removing() and exitcode != 0:
            msg = 'Dead container `{}`\nexit code: {}\nOOMKilled: {}\ncitadel url: {}\ncontainer log: {}'.format(
                container,
                exitcode,
                container.info.get('State', {}).get('OOMKilled', None),
                url_for('app.app', name=appname, _external=True),
                make_kibana_url(appname=appname, ident=container.ident),
            )
    elif healthy:
        container.mark_initialized()
        update_elb_for_containers(container)
        logger.debug('Healthy condition: [%s, %s, %s] ADD [%s, %s] [%s]', container.appname, container.podname, container.entrypoint, container_id, container.ident, ','.join(container.get_backends()))
    else:
        update_elb_for_containers(container, UpdateELBAction.REMOVE)
        if container.initialized and not container.is_removing():
            logger.debug('Sick condition: [%s, %s, %s] DEL [%s, %s] [%s]', container.appname, container.podname, container.entrypoint, container_id, container.ident, ','.join(container.get_backends()))
            msg = 'Sick container `{}`\ncitadel url: {}\nkibana log: {}'.format(
                container,
                url_for('app.app', name=appname, _external=True),
                make_kibana_url(appname=appname, ident=container.ident)
            )
        else:
            container.mark_initialized()
            logger.debug('Initial sick condition: [%s, %s, %s] DEL [%s, %s] [%s]', container.appname, container.podname, container.entrypoint, container_id, container.ident, ','.join(container.get_backends()))

    notbot_sendmsg(subscribers, msg)


@current_app.task(bind=True)
def trigger_tackle_routine(self):
    """
    gather all apps that has tackle rule defined, and check each rule to
    decide what strategy to apply (async)
    should only run within celery worker
    """
    apps = App.get_apps_with_tackle_rule()
    for app in apps:
        tackle_single_app.delay(app.name)


def schedule_task(app):
    appname = app.name
    release = app.latest_release
    if not release.image:
        logger.debug('Crontab skipped, %s not built yet', release)
        return
    specs = app.specs
    for crontab, cmd in specs.crontab:
        if not crontab.next(default_utc=False) < 60:
            logger.debug('Crontab not due: %s:%s', appname, cmd)
            continue
        combo = specs.combos[cmd]
        this_cronjob_containers = Container.get_by(entrypoint=combo.entrypoint, appname=appname)
        if this_cronjob_containers and set(c.status() for c in this_cronjob_containers) != {'running'}:
            notbot_sendmsg(app.subscribers, '{} cronjob skipped, because last cronjob container {} did not exit cleanly'.format(app, this_cronjob_containers))
            continue
        deploy_options = make_deploy_options(
            release, combo_name=cmd,
        )
        create_container.delay(deploy_options=deploy_options,
                               sha=release.sha,
                               envname=combo.envname)


@current_app.task
def trigger_scheduled_task():
    for app in App.get_all(limit=None):
        specs = app.specs
        cron_settings = specs and specs.crontab
        if not cron_settings:
            continue
        logger.debug('Scheduling task for app %s', app.name)
        schedule_task(app)


@current_app.task
def tackle_single_app(appname):
    app = App.get_by_name(appname)
    rule = app.tackle_rule
    app_status_assembler = app.app_status_assembler
    # check container status
    for rule in rule.get('container_tackle_rule', []):
        for c in app_status_assembler.container_status:
            dangers = c.eval_expressions(rule['situations'])
            if dangers:
                method = container_tackle_strategy_lib[rule['strategy']]
                logger.warn('%s container %s in DANGER: %s, tackle strategy %s', appname, c, dangers, method)
                method(c, dangers, **rule.get('kwargs', {}))


@current_app.task
def trigger_backup():
    for container in Container.get_all(limit=None):
        backup_path = container.backup_path
        if not container.backup_path:
            continue
        for path in backup_path:
            backup.delay(container.container_id, path)


@current_app.task
def backup(container_id, src_path):
    container = Container.get_by_container_id(container_id)
    try:
        result = get_core(container.zone).backup(container.container_id, src_path)
    except RpcError as e:
        notbot_sendmsg(container.app.subscribers, 'Backup container {} failed, err: {}'.format(container_id, e))
        return

    error = result.error
    if error:
        notbot_sendmsg(container.app.subscribers, 'Backup container {} failed, err: {}'.format(container_id, error))


def celery_task_stream_response(celery_task_ids):
    if isinstance(celery_task_ids, str):
        celery_task_ids = celery_task_ids,

    task_progress_channels = [TASK_PUBSUB_CHANNEL.format(task_id=id_) for id_ in celery_task_ids]
    pubsub = rds.pubsub()
    pubsub.subscribe(task_progress_channels)
    for item in pubsub.listen():
        # each content is a single JSON encoded grpc message
        raw_content = item['data']
        # omit the initial message where item['data'] is 1L
        if isinstance(raw_content, int):
            continue
        content = raw_content.decode('utf-8')
        logger.debug('Got pubsub message: %s', content)
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
    if isinstance(celery_task_ids, str):
        celery_task_ids = celery_task_ids,

    for task_id in celery_task_ids:
        async_result = AsyncResult(task_id)
        async_result.wait(timeout=120, propagate=False)
        if async_result.failed():
            yield json.dumps({'success': False, 'error': async_result.traceback})


class TackleTask(current_app.Task):
    """add custom rate limit functionality on top of EruGRPCTask
    do not frequently execute the same task for one smart_status"""
    def __call__(self, smart_status, dangers, **kwargs):
        """yeah, TackleTask has fixed args, and custom kwargs"""
        cooldown = int(parse_timespan(kwargs.get('cooldown', '1m')))
        strategy = self.name
        key = CITADEL_TACKLE_TASK_THROTTLING_KEY.format(id_=smart_status.name, strategy=strategy)
        if key in rds:
            logger.debug('Skip tackle strategy {}'.format(strategy))
            return
        logger.debug('Mark {} with ttl {}'.format(key, cooldown))
        rds.setex(key, 'true', cooldown)
        super(TackleTask, self).__call__(smart_status, dangers, **kwargs)


@current_app.task(bind=True, base=TackleTask)
def respawn_container(self, container_status, dangers, **kwargs):
    """
    {
        "strategy": "respawn_container",
        "situations": ["(healthy == 0) * 2m"],
        "kwargs": {
            "floor": 2,
            "celling": 8,
            "notify": true
        }
    }
    """
    container = Container.get_by_container_id(container_status.name)
    if container.is_removing():
        return
    sha = container.sha
    cid = container_status.name
    if kwargs.get('notify'):
        msg = '*Container Respawn*\n```\ncid: {}\nsha: {}\nreason: {}\n```'.format(cid, sha, dangers)
        notbot_sendmsg(container.app.subscribers, msg)

    upgrade_container(cid, sha)


@current_app.task(bind=True, base=TackleTask)
def send_warning(self, container_status, dangers, **kwargs):
    """
    send notification (via notbot) to app subscribers
    {
        "strategy": "send_warning",
        "situations": ["(healthy == 0) * 2m"],
    }
    """
    container = Container.get_by_container_id(container_status.name)
    msg = '*Citadel Warning*\nDangers:\n`{}`\nContainer status:\n```\n{}\n```'.format(dangers, container_status)
    notbot_sendmsg(container.app.subscribers, msg)


container_tackle_strategy_lib = {
    'respawn_container': respawn_container,
    'send_warning': send_warning,
}
app_tackle_strategy_lib = {}
