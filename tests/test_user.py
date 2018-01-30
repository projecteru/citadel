# -*- coding: utf-8 -*-

from flask import url_for, current_app


def test_login(test_db, client):
    current_app.config['DEBUG'] = False
    url = url_for('app.list_app')
    res = client.get(url)
    assert res.status_code == 302
