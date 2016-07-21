# coding: utf-8

from flask import g, request, abort

from citadel.ext import core
from citadel.libs.view import create_ajax_blueprint, DEFAULT_RETURN_VALUE
from citadel.views.helper import bp_get_app
from citadel.action import remove_container, ActionError

from citadel.models.app import AppUserRelation
from citadel.models.env import Environment
from citadel.models.balancer import LoadBalancer, add_record_analysis, delete_record_analysis


bp = create_ajax_blueprint('ajax', __name__, url_prefix='/ajax')


@bp.route('/app/<name>/delete-env', methods=['POST'])
def delete_app_env(name):
    envname = request.form['env']
    app = bp_get_app(name, g.user)
    env = Environment.get_by_app_and_env(app.name, envname)
    if env:
        env.delete()
    return DEFAULT_RETURN_VALUE


@bp.route('/rmcontainer', methods=['POST'])
def remove_containers():
    container_ids = request.form.getlist('container_id')
    try:
        return eru.remove_containers(container_ids)
    except EruException:
        return {'tasks': []}


@bp.route('/app/<name>/backends')
def get_app_backends(name):
    return {}


@bp.route('/pods')
def get_all_pods():
    return core.list_pods()


@bp.route('/pod/<name>/hosts')
def get_pod_nodes(name):
    return core.get_pod_nodes(name)


#@bp.route('/loadbalance', methods=['POST'])
#def create_loadbalance():
#    image = request.form['image']
#    name, sha = parse_name_and_version(image)
#    version = bp_get_version(name, sha)
#
#    podname = request.form['podname']
#    entrypoint = request.form['entrypoint']
#    balancer_name = request.form['name']
#    ncore = request.form.get('ncore', type=float, default=1)
#    hostname = request.form.get('hostname')
#    comment = request.form.get('comment', '')
#    envs = request.form.get('env', '')
#
#    if hostname == '_random':
#        hostname = None
#
#    extra_env = {'ELBNAME': name}
#    for env in envs.split(';'):
#        env = env.strip()
#        r = env.split('=', 1)
#        if len(r) != 2:
#            continue
#        extra_env.update({r[0].strip(): r[1].strip()})
#
#    @with_appcontext
#    def poll_loadbalance_container(task_id, user_id, comment):
#        container_id = None
#        while True:
#            try:
#                task = eru.get_task(task_id)
#            except EruException:
#                break
#            if not task['finished']:
#                gevent.sleep(1)
#                continue
#            try:
#                container_id = task['props']['container_ids'][0]
#            except (KeyError, IndexError):
#                pass
#            if container_id:
#                break
#
#        container = Container.get(container_id)
#        if not container:
#            return
#
#        Balancer.create(container.host_ip, user_id, container.container_id, balancer_name, comment)
#
#    try:
#        resp = eru.deploy_private(podname, name, ncore, 1,
#                                  version.sha, entrypoint, env='prod', network_ids=[],
#                                  host_name=hostname, extra_env=extra_env)
#        task_id = resp['tasks'][0]
#    except (EruException, IndexError, KeyError) as e:
#        return {'error': e.message}, 400
#
#    gevent.spawn(poll_loadbalance_container, task_id, g.user.id, comment)
#    return {'task': task_id}
#
#
@bp.route('/loadbalance/<id>/remove', methods=['POST'])
def remove_loadbalance(id):
    elb = bp_get_balancer(id)
    try:
        q = remove_container([elb.container_id])
    except ActionError as e:
        return {'error': e.message}

    # TODO 这里是同步的... 会不会太久
    for m in action_stream(q):
        if m.success and elb.container_id == m.id:
            elb.delete()
    return DEFAULT_RETURN_VALUE


@bp.route('/loadbalance/<id>/refresh', methods=['POST'])
def refresh_loadbalance(id):
    balancer = bp_get_balancer(id)
    balancer.refresh_records()
    return DEFAULT_RETURN_VALUE


@bp.route('/loadbalance/<id>/route', methods=['POST'])
def create_loadbalance_route(id):
    balancer = bp_get_balancer(id)

    appname = request.form['appname']
    domain = request.form['domain']
    entrypoint = request.form['entrypoint']

    balancer.add_record(appname, entrypoint, domain)
    return DEFAULT_RETURN_VALUE


#@bp.route('/loadbalance/record/<id>/remove', methods=['POST'])
#def delete_lbrecord(id):
#    record = bp_get_lbrecord(id)
#    record.delete()
#    return DEFAULT_RETURN_VALUE
#
#
#@bp.route('/loadbalance/srecord/<id>/remove', methods=['POST'])
#def delete_slbrecord(id):
#    srecord = bp_get_slbrecord(id)
#    srecord.delete()
#    return DEFAULT_RETURN_VALUE
#
#
#@bp.route('/loadbalance/record/<id>/analysis', methods=['PUT', 'DELETE'])
#def switch_lbrecord_analysis(id):
#    record = bp_get_lbrecord(id)
#    if request.method == 'PUT':
#        add_record_analysis(record)
#    elif request.method == 'DELETE':
#        delete_record_analysis(record)
#    return DEFAULT_RETURN_VALUE
#
#
#@bp.route('/loadbalance/for/<appname>/<entrypoint>')
#def get_balancer_for_app(appname, entrypoint):
#    records = LBRecord.get_by_appname_and_entrypoint(appname, entrypoint)
#    if not records:
#        return None
#    data = {'backend_name': records[0].backend_name}
#    balancers = set(r.balancer for r in records)
#    data['balancers'] = [b.to_dict() for b in balancers]
#    return data
#
#
#@bp.route('/loadbalance/forpod/<podname>/<appname>/<entrypoint>')
#def get_balancer_for_app_in_pod(podname, appname, entrypoint):
#    records = LBRecord.get_by_podname(podname, appname, entrypoint)
#    if not records:
#        return None
#    data = {'backend_name': records[0].backend_name}
#    balancers = set(r.balancer for r in records)
#    data['balancers'] = [b.to_dict() for b in balancers]
#    return data
#
#
@bp.route('/admin/revoke-app', methods=['POST'])
def revoke_app():
    user_id = request.form['user_id']
    name = request.form['name']
    AppUserRelation.delete(name, user_id)
    return DEFAULT_RETURN_VALUE
#
#
#@bp.before_request
#def access_control():
#    if request.path.startswith('/ajax/loadbalance/for') or request.path.endswith('/backends'):
#        return
#    if not g.user:
#        abort(401)
#    if not g.user.privilege and request.path.startswith('/ajax/admin'):
#        abort(403)
