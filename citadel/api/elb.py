# -*- coding: utf-8 -*-

from elb import ELBRespError
from flask import g, abort, request
from sqlalchemy.exc import SQLAlchemyError
from webargs.flaskparser import use_args

from citadel.config import ELB_BACKEND_NAME_DELIMITER
from citadel.libs.validation import CreateELBRulesSchema
from citadel.libs.view import DEFAULT_RETURN_VALUE, create_api_blueprint, user_require
from citadel.models.elb import ELBInstance, ELBRuleSet


bp = create_api_blueprint('elb', __name__, url_prefix='elb')


@bp.route('/')
@user_require(True)
def get_elbs():
    return ELBInstance.get_by_zone(g.zone)


def get_elb(elb_id):
    elb = ELBInstance.get(elb_id)
    if not elb:
        abort(404, 'ELB %s not found' % elb_id)
    return elb


# 获取和删除用id, 因为删除可能只删除其中一个.
@bp.route('/<elb_id>', methods=['GET', 'DELETE'])
@user_require(True)
def elb_instance(elb_id):
    elb = get_elb(elb_id)

    if request.method == 'GET':
        return elb

    elb.delete()
    return DEFAULT_RETURN_VALUE


@bp.route('/<elbname>/rules')
@user_require(True)
def get_elb_rules(elbname):
    elbs = ELBInstance.get_by(name=elbname, zone=g.zone)
    if not elbs:
        abort(404, 'No ELB named {} in zone {}'.format(elbname, g.zone))

    return ELBRuleSet.query.filter_by(elbname=elbname, zone=g.zone).all()


@bp.route('/<elbname>/rules', methods=['POST'])
@use_args(CreateELBRulesSchema())
@user_require(True)
def create_elb_rules(args, elbname):
    elbs = ELBInstance.get_by(name=elbname, zone=g.zone)
    if not elbs:
        abort(404, 'No ELB named {} in zone {}'.format(elbname, g.zone))

    appname = args['appname']
    podname = args['podnam']
    entrypoint = args['entrypoint_name']
    domain = args['domain']
    arguments = args['arguments']

    # 给一个简单挂容器后端的接口
    # 不需要arguments这种复杂参数
    # 只提供最简单的挂后端
    # TODO 有path加上path吧
    if not arguments:
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
        ruleset = ELBRuleSet.create(appname, podname, entrypoint, elbname,
                                    g.zone, domain, arguments)
    except (ValueError, SQLAlchemyError) as e:
        abort(400, e)

    client = ruleset.get_elbset()
    try:
        client.set_domain_rules(domain, ruleset.to_elbruleset())
        client.dump_to_etcd()
    except ELBRespError as e:
        # 不给500是为了方便抓住吧, 好像没抓500的
        abort(400, 'set domain rules error: %s' % e)
    return DEFAULT_RETURN_VALUE


@bp.route('/rule/<ruleset_id>')
@user_require(True)
def elb_ruleset(ruleset_id):
    ruleset = ELBRuleSet.get(ruleset_id)
    if not ruleset:
        abort(404, 'ELBRuleSet %s not found' % ruleset_id)
    return ruleset
