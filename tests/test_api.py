# -*- coding: utf-8 -*-
import json
from flask import url_for
from humanfriendly import parse_size

from .prepare import default_appname, make_specs_text, default_port, make_specs
from citadel.models.app import Release


json_headers = {'Content-Type': 'application/json'}


def test_register_app(test_db, client):
    appname = 'python-helloworld'
    sha = '3ff0138208ce41693d8ab1b96326b660cad34bef'
    git = 'git@github.com:dbarnett/python-helloworld.git'
    entrypoints = {
        'web': {
            'cmd': 'python -m http.server',
            'ports': default_port,
        },
        'hello': {
            'cmd': 'python helloworld.py',
        },
    }
    specs_text = make_specs_text(appname=appname, entrypoints=entrypoints)
    specs = make_specs(appname=appname, entrypoints=entrypoints)
    app_data = {
        'appname': appname,
        'git': git,
        'sha': sha,
        'specs_text': specs_text,
        'branch': 'master',
        'commit_message': '我一定行',
        'author': 'timfeirg',
    }
    res = client.post(url_for('app_v1.register_release'),
                      data=json.dumps(app_data),
                      headers=json_headers)
    assert res.status_code == 200
    release = Release.get_by_app_and_sha(appname, sha[:7])
    assert release.app.git == git
    assert release.commit_message == '我一定行'
    assert release.specs._raw == specs._raw

    # test duplicate, and test POST using HTTP form BTW
    res = client.post(url_for('app_v1.register_release'),
                      data=app_data)
    assert res.status_code == 400
    response_text = res.data.decode('utf-8')
    assert 'IntegrityError' in response_text


def test_combo(test_db, client):
    data = {
        'name': 'prod',
        'entrypoint_name': 'web',
        'podname': 'release',
        'networks': ['release'],
        'cpu_quota': 4.5,
        'memory': '512MB',
        'count': 4,
        'envname': 'prod',
    }
    res = client.post(url_for('app_v1.create_combo', appname=default_appname),
                      data=json.dumps(data),
                      headers=json_headers)
    assert res.status_code == 200
    combo = json.loads(res.data)
    assert combo['cpu_quota'] == 4.5
    assert combo['memory'] == parse_size('512MB', binary=True)
    assert combo['networks'] == ['release']

    res = client.delete(url_for('app_v1.delete_combo', appname=default_appname),
                        data=json.dumps({'name': 'prod'}),
                        headers=json_headers)
    assert res.status_code == 200

    # test typo
    data['network'] = data.pop('networks')
    res = client.post(url_for('app_v1.create_combo', appname=default_appname),
                      data=json.dumps(data),
                      headers=json_headers)
    assert res.status_code == 422
