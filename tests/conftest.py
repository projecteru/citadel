# coding: utf-8

import pytest
from urlparse import urlparse

from citadel import flask_app as app
from citadel.ext import db, rds


@pytest.fixture
def app(request):
    app.config['TESTING'] = True

    ctx = app.app_context()
    ctx.push()

    def clean_context():
        ctx.pop()

    request.addfinalizer(clean_context)
    return app


@pytest.yield_fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_db(request, app):

    def check_service_host(uri):
        """只能在本地或者容器里跑测试"""
        u = urlparse(uri)
        return u.hostname in ('localhost', '127.0.0.1') or 'hub.ricebook.net__ci__' in u.hostname

    if not (check_service_host(app.config['SQLALCHEMY_DATABASE_URI']) and check_service_host(app.config['REDIS_URL'])):
        raise Exception('Need to run test on localhost or in container')

    db.create_all()

    def teardown():
        db.session.remove()
        db.drop_all()
        rds.flushdb()

    request.addfinalizer(teardown)
