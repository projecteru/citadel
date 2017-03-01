# -*- coding: utf-8 -*-
from citadel.config import DEFAULT_ZONE
from citadel.models.specs import Specs, Entrypoint, Combo, FIVE_MINUTES


specs_text = '''
appname: "test-ci"
entrypoints:
  rsyslog:
    cmd: "python rsyslog_test.py"
    ports:
      - "5000/tcp"
    restart: "always"
    healthcheck_url: "/healthcheck"
    healthcheck_expected_code: 200
  test:
    after_start: "sh after_start"
    cmd: "gunicorn app:app --bind 0.0.0.0:5000"
    before_stop: "sh before_stop"
    ports:
      - "5000/tcp"
  web:
    cmd: "python run.py"
    ports:
      - "5000/tcp"
    restart: "always"
    healthcheck_url: "/healthcheck"
    healthcheck_expected_code: 200
    permdir: true
    publish_path: "/rhllor/service/com.platform.test"
  web-bad-health-no-check:
    cmd: "python run.py --interval 15"
    ports:
      - "5000/tcp"
  web-host:
    cmd: "python run.py --port 43345"
    ports:
      - "43345/tcp"
    network_mode: "host"
  none:
    cmd: "echo foo"
build:
  - "curl www.baidu.com"
  - "pip install -r requirements.txt"
base: "hub.ricebook.net/base/centos:python-latest"
subscribers: "#platform"
mount_paths:
  - "/var/www/html"
  - "/data/test-ci"
permitted_users:
  - "cmgs"
  - "zhangye"
combos:
  test:
    cpu: 1
    memory: "512MB"
    podname: "develop"
    entrypoint: "web"
    networks:
      - "release"
    extra_env: "FOO=bar;"
    permitted_users:
      - "tonic"
      - "liuyifu"
  prod:
    cpu: 1
    memory: "512MB"
    podname: "develop"
    entrypoint: "web"
    networks:
      - "release"
    permitted_users:
      - "liuyifu"
      - "tonic"
  cron:
    cpu: 1
    memory: "512MB"
    podname: "develop"
    zone: "c1"
    entrypoint: "cron"
    networks:
      - "c1-test2"
crontab:
  - '* * * * * cron'
'''


def test_specs():
    specs = Specs.from_string(specs_text)
    assert specs.appname == 'test-ci'

    entrypoints = specs.entrypoints
    rsyslog_entrypoint_data = {
        'command': 'python rsyslog_test.py',
        'ports': [{'protocol': u'tcp', 'port': 5000}],
        'restart': 'always',
        'healthcheck_url': '/healthcheck',
        'healthcheck_expected_code': 200,
        'permdir': False,
        'privileged': False,
    }
    left_entrypoint = entrypoints['rsyslog']
    right_entrypoint = Entrypoint(_raw=rsyslog_entrypoint_data, **rsyslog_entrypoint_data)
    assert left_entrypoint == right_entrypoint
    assert len(entrypoints) == 6

    assert specs.build == ['curl www.baidu.com', 'pip install -r requirements.txt']
    assert specs.base == 'hub.ricebook.net/base/centos:python-latest'
    assert specs.mount_paths == ["/var/www/html", "/data/test-ci"]

    combos = specs.combos
    combo_data = {'count': 1, 'memory': 536870912, 'cpu': 1, 'entrypoint': u'web', 'podname': u'develop', 'permitted_users': [u'tonic', u'liuyifu'], 'networks': [u'release'], 'zone': DEFAULT_ZONE, 'extra_env': {'FOO': 'bar'}, 'envname': ''}
    left_combo = combos['test']
    right_combo = Combo(_raw=combo_data, **combo_data)
    assert left_combo == right_combo
    assert left_combo.env_string == 'FOO=bar'
    assert left_combo.allow('tonic') is True
    assert left_combo.allow('cmgs') is False

    assert specs.permitted_users == {'tonic', 'liuyifu', 'cmgs', 'zhangye'}
    assert specs.subscribers == '#platform'
    assert specs.erection_timeout == FIVE_MINUTES
    # TODO: test crontab, wait for
    # https://github.com/josiahcarlson/parse-crontab/pull/23
