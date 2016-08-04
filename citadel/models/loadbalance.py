# coding: utf-8

import requests
from sqlalchemy.exc import IntegrityError
from collections import Iterable

from citadel.ext import db
from citadel.libs.json import Jsonized
from citadel.libs.utils import normalize_domain
from citadel.models.base import BaseModelMixin
from citadel.models.container import Container


"""
配合ELB的部分.
现在ELB实际按照名字来区别, 名字相同的多个ELB实例认为是一个ELB的多个实例.
路由记录挂载在名字上, 也就是说名字相同的一组ELB实例实际上的等价的.
所有对路由记录的操作, 都会反应到对应的所有ELB实例上.
"""


def get_app_backends(podname, appname, entrypoint):
    containers = Container.get_by_app(appname, limit=100)
    if entrypoint == '_all':
        return [b for c in containers for b in c.get_backends() if c.podname == podname]
    return [b for c in containers for b in c.get_backends() if c.entrypoint == entrypoint and c.podname == podname]


class Route(BaseModelMixin):
    """
    ELB的route. 把appname/entrypoint/podname对应的一组backend给路由到对应elbname的ELB上.
    用名字来对应, 也就是说一组名字相同的ELB互为热备, 他们具有同样的路由.
    """
    __tablename__ = 'elb_route'
    __table_args = (
        db.UniqueConstraint('elbname', 'appname', 'entrypoint'),
    )

    elbname = db.Column(db.String(64), index=True)
    appname = db.Column(db.String(255), index=True)
    entrypoint = db.Column(db.String(255), index=True)
    podname = db.Column(db.String(255))
    domain = db.Column(db.String(255))

    def __hash__(self):
        return self.id

    @classmethod
    def create(cls, podname, appname, entrypoint, domain, elbname):
        backends = get_app_backends(podname, appname, entrypoint)
        if not backends:
            return

        domain = normalize_domain(domain)

        try:
            r = cls(appname=appname, entrypoint=entrypoint,
                    domain=domain, elbname=elbname, podname=podname)
            db.session.add(r)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None

        add_route(r)
        return r

    @classmethod
    def get_by_elb(cls, elbname):
        return cls.query.filter_by(elbname=elbname).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_backend(cls, appname, entrypoint, podname):
        return cls.query.filter_by(appname=appname, entrypoint=entrypoint, podname=podname).order_by(cls.id.desc()).all()

    @property
    def backend_name(self):
        return '%s_%s_%s' % (self.appname, self.podname, self.entrypoint)

    def get_elb(self):
        return ELBInstance.get_by_name(self.elbname)

    def get_backends(self):
        return get_app_backends(self.podname, self.appname, self.entrypoint)

    def delete(self):
        delete_route(self)
        super(Route, self).delete()


class ELBInstance(BaseModelMixin):
    """name 相同的 ELBInstance 组成一个 ELB, ELB 是一个虚拟的概念"""
    __tablename__ = 'elb'

    addr = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    container_id = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(64))
    comment = db.Column(db.Text)

    def __hash__(self):
        return self.id

    @classmethod
    def create(cls, addr, user_id, container_id, name, comment=''):
        b = cls(addr=addr, user_id=user_id, container_id=container_id, name=name, comment=comment)
        db.session.add(b)
        db.session.commit()
        return b

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_container_id(cls, container_id):
        return cls.query.filter(cls.container_id.like('{}%'.format(container_id))).first()

    @property
    def lb_client(self):
        return LBClient(self.addr)

    @property
    def container(self):
        return Container.get_by_container_id(self.container_id)

    @property
    def ip(self):
        """要么是容器的IP, 要么是宿主机的IP, 反正都可以从容器那里拿到."""
        if not self.container:
            return 'Unknown'
        ips = self.container.get_ips()
        return ips and ips[0] or 'Unknown'

    def is_alive(self):
        return self.container and self.container.status() == 'running'

    def get_all_analysis(self):
        return self.lb_client.get_analysis() or {}

    def to_dict(self):
        d = {}
        d['user_id'] = self.user_id
        d['lb_client'] = self.lb_client.to_dict()
        d['name'] = self.name
        return d


class LBClient(Jsonized):

    def __init__(self, addr):
        if not addr.startswith('http://'):
            addr = 'http://%s' % addr
        self.addr = addr
        self.domain_addr = '%s/__erulb__/domain' % addr
        self.upstream_addr = '%s/__erulb__/upstream' % addr
        self.analysis_addr = '%s/__erulb__/analysis' % addr

    def _get(self, url):
        resp = requests.get(url)
        return resp.status_code == 200 and resp.json() or None

    def _put(self, url, data):
        resp = requests.put(url, json=data)
        return resp.status_code == 200

    def _delete(self, url, data):
        resp = requests.delete(url, json=data)
        return resp.status_code == 200

    def get_domain(self):
        return self._get(self.domain_addr)

    def update_domain(self, backend_name, domain):
        data = {'backend': backend_name, 'name': domain}
        return self._put(self.domain_addr, data)

    def delete_domain(self, domain):
        data = {'name': domain}
        return self._delete(self.domain_addr, data)

    def get_upstream(self):
        return self._get(self.upstream_addr)

    def update_upstream(self, backend_name, servers):
        data = {'backend': backend_name, 'servers': servers}
        return self._put(self.upstream_addr, data)

    def delete_upstream(self, backend_name):
        data = {'backend': backend_name}
        return self._delete(self.upstream_addr, data)

    def add_analysis(self, domain):
        if not isinstance(domain, list):
            domain = [domain]
        data = {'hosts': domain}
        return self._put(self.analysis_addr, data)

    def delete_analysis(self, domain):
        data = {'host': domain}
        return self._delete(self.analysis_addr, data)

    def get_analysis(self):
        return self._get(self.analysis_addr)

    def to_dict(self):
        return {'domain_addr': self.domain_addr, 'upstream_addr': self.upstream_addr}


def add_route(route):
    """把一条路由添加到ELB内存里.
    获取所有关联的ELB, 挨个添加记录."""
    # 获取upstream servers
    # 现在还没加 weight
    # 但是如果没有后端就算了, 也不添加domain了
    servers = ['server %s;' % b for b in route.get_backends()]
    if not servers:
        return

    for elb in route.get_elb():
        client = elb.lb_client
        # 1. 添加upstream
        client.update_upstream(route.backend_name, servers)
        # 2. 添加domain
        client.update_domain(route.backend_name, route.domain)


def delete_route(route):
    """把一条路由从ELB内存里删除.
    要先看看对应的backend_name还有没有别人在用, 没有的话连upstream一起删除.
    有的话只删除对应的域名, 也就是取消域名跟upstream的关联.
    """
    # 先检查(appname, entrypoint, podname)这个三元组还有没有别人在用
    rs = Route.get_by_backend(route.appname, route.entrypoint, route.podname)
    rs = [r for r in rs if r != route]

    for elb in route.get_elb():
        client = elb.lb_client
        # 1. 删除domain
        client.delete_domain(route.domain)

        # 如果没有别人在用了
        # 2. 删除upstream
        if not rs:
            client.delete_upstream(route.backend_name)


def refresh_routes(name):
    """刷新一下名为name的ELB的路由表.
    把对应的路由记录取出来, 然后对所有关联上的ELB实例进行刷新.
    记录已经存在也没有关系, ELB自己会忽略掉错误."""
    routes = Route.get_by_elb(name)
    for r in routes:
        add_route(r)


def add_route_analysis(route):
    for elb in route.get_elb():
        client = elb.lb_client
        client.add_analysis(route.domain)


def delete_route_analysis(route):
    for elb in route.get_elb():
        client = elb.lb_client
        client.delete_analysis(route.domain)


def update_elb_for_containers(containers):
    if not isinstance(containers, Iterable):
        containers = [containers]

    route_backends = set((c.appname, c.entrypoint, c.podname) for c in containers)

    for appname, entrypoint, podname in route_backends:
        routes = Route.get_by_backend(appname, entrypoint, podname)
        if not routes:
            continue
        elbnames = set(r.elbname for r in routes)
        elbs = [elb for elb_list in [ELBInstance.get_by_name(n) for n in elbnames] for elb in elb_list]
        lb_clients = [elb.lb_client for elb in elbs]

        # routes 就是不同 ELB 上边的 route 组成的数组
        # 它们其实是一样的路由，随便取一个 backend_name 就好了
        backend_name = routes[0].backend_name
        backends = get_app_backends(podname, appname, entrypoint)
        servers = ['server %s;' % b for b in backends]
        for lb_client in lb_clients:
            lb_client.update_upstream(backend_name, servers)
