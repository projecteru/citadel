# -*- coding: utf-8 -*-
import json
from flask import url_for
from humanfriendly import parse_size

from .test_specs import make_specs, default_appname, make_specs_text
from citadel.models.app import Release


json_headers = {'Content-Type': 'application/json'}


def test_register_app(test_db, client):
    # test app related APIs
    app_data = {
        'name': default_appname,
        'git': 'git@github.com:projecteru2/citadel.git',
        'sha': '13bba2286f2112316703f1675061322ddd730a04',
        'specs_text': make_specs_text(),
        'branch': 'next-gen',
        'commit_message': '我一定行',
        'author': 'timfeirg',
    }
    res = client.post(url_for('app_v1.register_release'),
                      data=json.dumps(app_data),
                      headers=json_headers)
    assert res.status_code == 200
    release = Release.get_by_app_and_sha(default_appname, '13bba22')
    assert release.app.git == 'git@github.com:projecteru2/citadel.git'
    assert release.commit_message == '我一定行'
    assert release.specs._raw == make_specs()._raw

    # test combo related APIs
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
