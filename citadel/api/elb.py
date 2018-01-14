# -*- coding: utf-8 -*-

from flask import g, abort
from flask import request

from elb import ELBRespError

from citadel.tasks import create_elb_instance
from citadel.libs.view import DEFAULT_RETURN_VALUE
from citadel.libs.view import create_api_blueprint

from citadel.config import ELB_BACKEND_NAME_DELIMITER
from citadel.models.elb import ELBInstance
from citadel.models.elb import ELBRuleSet


bp = create_api_blueprint('elb', __name__, url_prefix='elb')


@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return ELBInstance.get_by_zone(g.zone)

    payload = request.get_json()
    if not payload:
        abort(400, 'bad JSON data')

    combo_name = payload.get('combo_name', '')
    name = payload.get('name', '')
    sha = payload.get('sha', '')
    nodename = payload.get('nodename', '')
    if not (combo_name and name and sha):
        abort(400, 'bad JSON data')

    # 先这样吧
    # TODO 晚点改成websocket
    create_elb_instance.delay(g.zone, combo_name, name, sha, nodename, g.user_id)
    return DEFAULT_RETURN_VALUE


def get_elb(elb_id):
    elb = ELBInstance.get(elb_id)
    if not elb:
        abort(404, 'ELB %s not found' % elb_id)
    return elb


# 获取和删除用id, 因为删除可能只删除其中一个.
@bp.route('/<elb_id>', methods=['GET', 'DELETE'])
def elb_instance(elb_id):
    elb = get_elb(elb_id)

    if request.method == 'GET':
        return elb

    # 当是最后一个实例的时候
    # 删除掉里面的全部rules
    # TODO 不过这个到底有没有必要其实存疑? 删掉吧先
    if elb.is_only_instance():
        elb.clear_rules()
    elb.delete()
    return DEFAULT_RETURN_VALUE


# 规则需要用elbname, 因为是对一组elb, id有迷惑性.
# 或者说设计如此吧...
@bp.route('/<elbname>/rules', methods=['GET', 'POST'])
def elb_instance_rules(elbname):
    # 先得检测下elbname是不是有效的吧
    # 不能随便给个啥也给生成个ruleset啊
    elbs = ELBInstance.get_by(name=elbname, zone=g.zone)
    if not elbs:
        abort(404, 'bad elbname: %s' % elbname)

    if request.method == 'GET':
        return ELBRuleSet.query.filter_by(elbname=elbname, zone=g.zone).all()

    payload = request.get_json()
    if not payload:
        abort(400, 'bad JSON data')

    appname = payload.get('appname', '')
    podname = payload.get('podname', '')
    entrypoint = payload.get('entrypoint', '')
    domain = payload.get('domain', '')
    arguments = payload.get('arguments', {})
    if not all([appname, podname, entrypoint, domain]):
        abort(400, 'bad JSON data')

    simple = payload.get('simple')
    if not (simple or arguments):
        abort(400, 'provide either simple or arguments')

    # 给一个简单挂容器后端的接口
    # 不需要arguments这种复杂参数
    # 只提供最简单的挂后端
    # TODO 有path加上path吧
    if payload.get('simple'):
        servername = ELB_BACKEND_NAME_DELIMITER.join([appname, entrypoint, podname])
        arguments = {
            'init': 'backend',
            'rules': [
                {
                    'backend': {
                        'type': 'backend',
                        'args': {
                            'servername': servername,
                        }
                    },
                },
            ],
        }

    try:
        ruleset = ELBRuleSet.create(appname, podname, entrypoint,
                elbname, g.zone, domain, arguments)
    except ValueError as e:
        abort(400, e)

    if not ruleset:
        abort(400, 'create elb ruleset error')

    client = ruleset.get_elbset()
    try:
        client.set_domain_rules(domain, ruleset.to_elbruleset())
        client.dump_to_etcd()
    except ELBRespError as e:
        # 不给500是为了方便抓住吧, 好像没抓500的
        abort(400, 'set domain rules error: %s' % e)
    return DEFAULT_RETURN_VALUE


@bp.route('/rule/<ruleset_id>', methods=['GET'])
def elb_ruleset(ruleset_id):
    ruleset = ELBRuleSet.get(ruleset_id)
    if not ruleset:
        abort(404, 'ELBRuleSet %s not found' % ruleset_id)
    return ruleset
