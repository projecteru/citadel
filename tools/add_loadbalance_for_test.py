# coding: utf-8

import os
import sys
import hashlib
import random
sys.path.append(os.path.abspath('.'))

from citadel.ext import db
from citadel.libs.utils import with_appcontext
from citadel.models.loadbalance import ELBInstance, Route


@with_appcontext
def add_elb():
    for _ in range(3):
        num = random.randint(1, 110)
        container_id = hashlib.sha256(str(num)).hexdigest()
        ELBInstance.create('10.0.0.%s' % num, container_id, 'ELB-External', 'ELB for external network')

    for _ in range(3):
        num = random.randint(111, 255)
        container_id = hashlib.sha256(str(num)).hexdigest()
        ELBInstance.create('10.0.0.%s' % num, container_id, 'ELB-Internal', 'ELB for internal network')

    ELBInstance.create('127.0.0.1', container_id, 'ELB-test', 'ELB for test')


@with_appcontext
def add_routes():
    r = Route(podname='dev', appname='test-ci', entrypoint='web', domain='citest.xxx.com', elbname='ELB-Internal')
    db.session.add(r)
    db.session.commit()
    r = Route(podname='dev', appname='test-ci2', entrypoint='web', domain='citest2.xxx.com', elbname='ELB-Internal')
    db.session.add(r)
    db.session.commit()
    r = Route(podname='dev', appname='test-ci', entrypoint='web', domain='citest.xxx.com', elbname='ELB-External')
    db.session.add(r)
    db.session.commit()
    r = Route(podname='dev', appname='test-ci2', entrypoint='web', domain='citest2.xxx.com', elbname='ELB-External')
    db.session.add(r)
    db.session.commit()


add_elb()
add_routes()
