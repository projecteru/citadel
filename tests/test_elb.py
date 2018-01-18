# coding: utf-8

import json
import pytest
from mock import MagicMock
from flask import url_for

from elb import RuleSet, ELBSet
from elb import PathRule, UARule, BackendRule

from citadel.models.elb import build_elb_rule
from citadel.models.elb import build_elb_ruleset
from citadel.models.elb import ELBRuleSet
from citadel.models.elb import ELBInstance

path_rule_value = {
    'name0': {
        'type': 'path',
        'args': {
            'succ': 'name1',
            'fail': 'name2',
            'pattern': '^test$',
            'regex': '',
            'rewrite': '',
        }
    }
}
ua_rule_value = {
    'name1': {
        'type': 'ua',
        'args': {
            'succ': 'name2',
            'fail': 'name2',
            'pattern': '^test$',
        }
    }
}
backend_rule_value = {
    'name2': {
        'type': 'backend',
        'args': {
            'servername': 'appname__entrypoint__podname'
        }
    }
}


def test_build_elb_rule(test_db):
    bad_value1 = {'name0': 'whatever', 'name1': 'whatever'}
    with pytest.raises(ValueError):
        build_elb_rule(bad_value1)
    bad_value2 = {'name0': {'type': 'badtype', 'args': {}}}
    with pytest.raises(ValueError):
        build_elb_rule(bad_value2)
    bad_value3 = {
        'name0': {
            'type': 'path',
            'args': {
                'succ': 'name1',
                'fail': 'name2',
                'whatever': '^test$',
            }
        }
    }
    with pytest.raises(TypeError):
        build_elb_rule(bad_value3)

    r = build_elb_rule(path_rule_value)
    assert r is not None
    assert isinstance(r, PathRule)

    r = build_elb_rule(ua_rule_value)
    assert r is not None
    assert isinstance(r, UARule)

    r = build_elb_rule(backend_rule_value)
    assert r is not None
    assert isinstance(r, BackendRule)


def test_build_elb_ruleset(test_db):
    arguments = {'init': '', 'rules': []}
    with pytest.raises(ValueError):
        build_elb_ruleset(arguments)
    arguments = {'init': 'whatever',
                 'rules': [ua_rule_value, path_rule_value, backend_rule_value]}
    with pytest.raises(ValueError):
        build_elb_ruleset(arguments)
    arguments = {'init': 'name0',
                 'rules': [ua_rule_value, path_rule_value, backend_rule_value]}
    rs = build_elb_ruleset(arguments)
    assert isinstance(rs, RuleSet)
    assert rs.check_rules()


def create_elb_instance(mocker):
    def get_c(i):
        if i == 'c1':
            return MagicMock(container_id='c1', zone='zone')
        if i == 'c2':
            return MagicMock(container_id='c2', zone='zone')

    mocker.patch('citadel.models.elb.Container.get_by_container_id', get_c)
    ELBInstance.create('10.10.101.1:8000', 'c1', 'elbname')
    ELBInstance.create('10.10.101.2:8000', 'c2', 'elbname')


def test_create_elbruleset(test_db, mocker):
    arguments = {'init': '', 'rules': []}
    with pytest.raises(ValueError):
        ELBRuleSet.create('appname', 'podname', 'entrypoint', 'elbname', 'zone', 'domain', arguments)
    arguments = {'init': 'whatever',
                 'rules': [ua_rule_value, path_rule_value, backend_rule_value]}
    with pytest.raises(ValueError):
        ELBRuleSet.create('appname', 'podname', 'entrypoint', 'elbname', 'zone', 'domain', arguments)
    arguments = {'init': 'name0',
                 'rules': [ua_rule_value, path_rule_value, backend_rule_value]}
    rs = ELBRuleSet.create('appname', 'podname', 'entrypoint', 'elbname', 'zone', 'domain', arguments)
    assert rs is not None
    ruleset = rs.to_elbruleset()
    assert isinstance(ruleset, RuleSet)
    assert ruleset.check_rules()

    brs = rs.get_backend_rule()
    assert len(brs) == 1
    br = brs[0]
    assert br.name == 'name2'
    assert br.servername == 'appname__entrypoint__podname'

    create_elb_instance(mocker)
    es = rs.get_elbset()
    assert isinstance(es, ELBSet)
    assert len(es.elbs) == 2


def test_api_index(test_db, mocker, client):
    resp = client.get(url_for('elb.index', zone='zone'))
    assert resp.status_code == 200
    r = json.loads(resp.data)
    assert len(r) == 0

    create_elb_instance(mocker)
    resp = client.get(url_for('elb.index', zone='zone'))
    assert resp.status_code == 200
    r = json.loads(resp.data)
    assert len(r) == 2
    ELBInstance.create('10.10.101.1:8000', 'c1', 'elbname')
    ELBInstance.create('10.10.101.2:8000', 'c2', 'elbname')
    assert [e['addr'] for e in r] == ['10.10.101.2:8000', '10.10.101.1:8000']
    assert [e['container_id'] for e in r] == ['c2', 'c1']
    assert [e['name'] for e in r] == ['elbname', 'elbname']
    assert [e['zone'] for e in r] == ['zone', 'zone']

    resp = client.post(url_for('elb.index', zone='zone'), data='')
    assert resp.status_code == 400
    r = json.loads(resp.data)
    assert r['error'] == 'bad JSON data'

    def client_post(url, data):
        return client.post(url, data=json.dumps(data),
                           headers={'content-type': 'application/json'})

    data = {'combo_name': 'combo_name', 'name': 'name'}
    resp = client_post(url_for('elb.index', zone='zone'), data)
    assert resp.status_code == 400
    r = json.loads(resp.data)
    assert r['error'] == 'bad JSON data'

    # TODO 接了core再说吧


def test_api_elb(test_db, mocker, client):
    resp = client.get(url_for('elb.elb_instance', zone='zone', elb_id=1))
    assert resp.status_code == 404
    r = json.loads(resp.data)

    create_elb_instance(mocker)

    ids = [e.id for e in ELBInstance.query.order_by(ELBInstance.id.desc()).all()]
    for idx, i in enumerate(ids):
        resp = client.get(url_for('elb.elb_instance', zone='zone', elb_id=i))
        assert resp.status_code == 200
        r = json.loads(resp.data)
        if idx == 0:
            assert r['addr'] == '10.10.101.2:8000'
            assert r['container_id'] == 'c2'
        if idx == 1:
            assert r['addr'] == '10.10.101.1:8000'
            assert r['container_id'] == 'c1'

    deleted_id, remained_id = ids
    resp = client.delete(url_for('elb.elb_instance', elb_id=deleted_id, zone='zone'))
    assert resp.status_code == 200

    resp = client.get(url_for('elb.elb_instance', elb_id=deleted_id, zone='zone'))
    assert resp.status_code == 404
    resp = client.get(url_for('elb.elb_instance', elb_id=remained_id, zone='zone'))
    assert resp.status_code == 200


def test_api_elb_rules(test_db, mocker, client):
    resp = client.get(url_for('elb.get_elb_rules', elbname='xxx', zone='zone'))
    assert resp.status_code == 404
    r = json.loads(resp.data)

    create_elb_instance(mocker)
    resp = client.get(url_for('elb.get_elb_rules', elbname='elbname', zone='zone'))
    assert resp.status_code == 200
    r = json.loads(resp.data)
    assert len(r) == 0

    def client_post(url, data):
        return client.post(url, data=json.dumps(data),
                           headers={'content-type': 'application/json'})

    data = {'appname': 'appname', 'podname': 'podname', 'entrypoint': 'entrypoint'}
    resp = client_post(url_for('elb.create_elb_rules', elbname='elbname', zone='zone'), data)
    assert resp.status_code == 422

    data['domain'] = 'domain'
    resp = client_post(url_for('elb.create_elb_rules', elbname='elbname', zone='zone'), data)
    assert resp.status_code == 422

    resp = client_post(url_for('elb.create_elb_rules', elbname='elbname', zone='zone'), data)
    # 没有elb啊这里当然会挂...
    # TODO 有了elb再说吧
    assert resp.status_code == 422
