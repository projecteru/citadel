# -*- coding: utf-8 -*-

import json
from celery import current_app
from grpc import RpcError, StatusCode
from humanfriendly import parse_timespan

from citadel.config import ZONE_CONFIG, CITADEL_TACKLE_TASK_THROTTLING_KEY, ELB_APP_NAME, TASK_PUBSUB_CHANNEL, BUILD_ZONE, CITADEL_HEALTH_CHECK_STATS_KEY
from citadel.ext import rds
from citadel.libs.exceptions import ActionError
from citadel.libs.jsonutils import VersatileEncoder
from citadel.libs.utils import notbot_sendmsg, logger
from citadel.models import Container, Release
from citadel.models.app import App
from citadel.models.container import ContainerOverrideStatus
from citadel.models.elb import update_elb_for_containers, UpdateELBAction, ELBInstance
from citadel.models.oplog import OPType, OPLog
from citadel.rpc.client import get_core


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
def build_image(self, appname, sha):
    release = Release.get_by_app_and_sha(appname, sha)
    specs = release.specs
    if release.raw:
        release.update_image(specs.base)
        return

    core = get_core(BUILD_ZONE)
    opts = release.make_core_build_options()
    build_messages = core.build_image(opts)
    for m in build_messages:
        self.stream_output(m)

    image_tag = m.progress
    release.update_image(image_tag)
    return image_tag


@current_app.task(bind=True)
def create_container(self, zone=None, user_id=None, appname=None, sha=None,
                     combo_name=None, debug=False, task_id=None):
    release = Release.get_by_app_and_sha(appname, sha)
    app = release.app
    combo = app.get_combo(combo_name)
    deploy_options = release.make_core_deploy_options(combo_name)
    ms = get_core(zone).create_container(deploy_options)

    bad_news = []
    deploy_messages = []
    for m in ms:
        self.stream_output(m, task_id=task_id)
        deploy_messages.append(m)

        if m.success:
            logger.debug('Creating container %s:%s got grpc message %s', appname, combo.entrypoint_name, m)
            override_status = ContainerOverrideStatus.DEBUG if debug else ContainerOverrideStatus.NONE
            Container.create(appname,
                             sha,
                             m.id,
                             m.name,
                             combo.entrypoint_name,
                             combo.envname,
                             combo.cpu_quota,
                             combo.memory,
                             zone,
                             m.podname,
                             m.nodename,
                             override_status=override_status)

            op_content = {'entrypoint': combo.entrypoint_name,
                          'envname': combo.envname,
                          'networks': combo.networks,
                          'container_id': m.id}
            OPLog.create(user_id,
                         OPType.CREATE_CONTAINER,
                         appname=appname,
                         sha=sha,
                         zone=zone,
                         content=op_content)
        else:
            bad_news.append(m)

    if bad_news:
        msg = 'Deploy {}\n*BAD NEWS*:\n```\n{}\n```\n'.format(
            appname,
            json.dumps(bad_news, cls=VersatileEncoder),
        )
        notbot_sendmsg(app.subscribers, msg)

    return deploy_messages


@current_app.task(bind=True)
def create_elb_instance(self, zone=None, combo_name=None, name=None, sha=None,
                        nodename=None, user_id=None):
    """按照zone和combo_name创建elb, 可能可以设定node"""
    messages = create_container(zone=zone,
                                user_id=user_id,
                                appname=ELB_APP_NAME,
                                sha=sha,
                                combo_name=combo_name,
                                nodename=nodename,
                                task_id=self.request.id)
    container_id = messages[0]['id']
    container = Container.get_by_container_id(container_id)
    if not container:
        raise ActionError('Cannot find container for elb: {}'.format(container_id))

    ips = container.get_ips()
    ELBInstance.create(ips[0], container.container_id, name)

    op_content = {'elbname': name, 'container_id': container.container_id}
    OPLog.create(user_id,
                 OPType.CREATE_ELB_INSTANCE,
                 appname=ELB_APP_NAME,
                 sha=sha,
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

    ms = get_core(zone).remove_container(full_ids)
    res = []
    for m in ms:
        self.stream_output(m)
        res.append(m)

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
        else:
            logger.error('Remove container %s got error: %s', m.id, m.message)
            notbot_sendmsg('#platform', 'Error removing container {}: {}\n@timfeirg'.format(m.id, m.message))

    return res


@current_app.task(bind=True)
def deal_with_agent_etcd_change(self, key, deploy_info):
    container_id = deploy_info['ID']
    healthy = deploy_info['Healthy']
    appname = deploy_info['Name']
    app = App.get_by_name(appname)
    container = Container.get_by_container_id(container_id)
    previous_deploy_info = container.deploy_info
    container.update_deploy_info(deploy_info)

    # TODO: use new ELB lib
    # 只要是健康, 无论如何也做一次 ELB 更新, 一方面是反正不贵,
    # 另一方面如果之前哪里出错了没更新成功, 下一次更新还有可能修好
    if healthy:
        logger.info('ELB: ADD [%s, %s, %s, %s, %s]', container.appname, container.podname, container.entrypoint_name, container_id, container.publish)
        update_elb_for_containers(container)
    else:
        logger.info('ELB: REMOVE [%s, %s, %s, %s, %s]', container.appname, container.podname, container.entrypoint_name, container_id, container.publish)
        update_elb_for_containers(container, UpdateELBAction.REMOVE)

    # 处理完了 ELB, 再根据前后状态决定要发什么报警信息
    subscribers = app.subscribers
    msg = ''

    # TODO: acquire exit-code
    # TODO: handle cronjob containers
    previous_healthy = previous_deploy_info.get('Healthy')
    if healthy:
        # 健康万岁
        if previous_healthy is None:
            # 容器第一次健康, 说明刚刚初始化好, 就不需要报警了, mark 一下就好
            container.mark_initialized()
        elif previous_healthy is False:
            # 容器病好了, 要汇报好消息, 但是如果是第一次病好,
            # 那说明只是初始化成功, 这种情况就没必要报警了,
            # 每个容器都会经历一次, 只需要 mark 一下就好
            if container.initialized:
                msg = 'Container resurge: {}'.format(container)
            else:
                container.mark_initialized()
        else:
            # 之前也健康, 那就不用管了
            pass
    else:
        # 生病了
        if previous_healthy is None:
            # 说明刚刚初始化好, 这时候不健康也是正常的, 可以忽略
            pass
        elif previous_healthy is False:
            # 之前就不健康, 那说明已经发过报警了, 就不要骚扰用户了
            pass
        else:
            # 之前是健康的, 现在病了, 当然要报警
            msg = 'Container sick: {}'.format(container)

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
        this_cronjob_containers = Container.get_by(entrypoint=combo.entrypoint_name, appname=appname)
        if this_cronjob_containers and set(c.status() for c in this_cronjob_containers) != {'running'}:
            notbot_sendmsg(app.subscribers, '{} cronjob skipped, because last cronjob container {} did not exit cleanly'.format(app, this_cronjob_containers))
            continue
        # FIXME:
        # deploy_options = make_deploy_options(
        #     release, combo_name=cmd,
        # )
        # create_container.delay(deploy_options=deploy_options,
        #                        sha=release.sha,
        #                        envname=combo.envname)


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
        if not isinstance(raw_content, (bytes, str)):
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

    # FIXME
    # upgrade_container(cid, sha)


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
