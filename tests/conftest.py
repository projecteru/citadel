# -*- coding: utf-8 -*-
import pytest
import subprocess
import threading
from urllib.parse import urlparse

from .prepare import default_appname, default_sha, default_git, make_specs_text, default_combo_name, default_podname, default_cpu_quota, default_memory, default_network_name
from citadel.app import create_app
from citadel.ext import db, rds
from citadel.libs.utils import logger
from citadel.models.app import App, Release, Combo


@pytest.fixture
def app(request):
    app = create_app()
    app.config['TESTING'] = True

    ctx = app.app_context()
    ctx.push()

    def tear_down():
        ctx.pop()

    request.addfinalizer(tear_down)
    return app


@pytest.fixture
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
    app = App.get_or_create(default_appname, git=default_git)
    Release.create(app, default_sha, make_specs_text())
    Combo.create(default_appname, default_combo_name, 'web', default_podname,
                 networks=[default_network_name], cpu_quota=default_cpu_quota,
                 memory=default_memory, count=1)

    def teardown():
        db.session.remove()
        db.drop_all()
        rds.flushdb()

    request.addfinalizer(teardown)


@pytest.fixture
def watch_etcd(request, test_db):
    p = subprocess.Popen(
        'bin/run-etcd-watcher --zone test-zone --sync'.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    logger.info('Starting watch_etcd process %s', p)

    def async_thread_output(p):
        while p.poll() is None:
            # A None value indicates that the process hasn't terminated yet.
            print(p.stdout.readline())

    t = threading.Thread(target=async_thread_output, args=(p, ))
    t.start()

    def teardown():
        logger.info('Terminating watch_etcd process %s', p)
        p.terminate()

    request.addfinalizer(teardown)
    return p
