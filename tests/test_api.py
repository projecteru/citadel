# -*- coding: utf-8 -*-
import json
from flask import url_for

from .test_specs import make_specs_text, make_specs
from citadel.models.app import Release


json_headers = {'Content-Type': 'application/json'}


def test_register_app(test_db, client):
    data = {
        'name': 'test-ci',
        'git': 'git@github.com:projecteru2/citadel.git',
        'sha': '13bba2286f2112316703f1675061322ddd730a04',
        'specs_text': make_specs_text(),
        'branch': 'next-gen',
        'commit_message': '我一定行',
        'author': 'timfeirg',
    }
    res = client.post(url_for('app_v1.register_release'),
                      data=json.dumps(data),
                      headers=json_headers)
    assert res.status_code == 200
    release = Release.get_by_app_and_sha('test-ci', '13bba22')
    assert release.app.git == 'git@github.com:projecteru2/citadel.git'
    assert release.commit_message == '我一定行'
    assert release.specs._raw == make_specs()._raw
