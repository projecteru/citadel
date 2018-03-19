.. _dev:

***********
Development
***********

Mac OS
======

.. sourcecode:: shell

   brew install mysql
   mysql -uroot -e 'CREATE DATABASE citadeltest'
   brew install python3
   mkvirtualenv citadel --python=python3
   pip install -r requirements-dev.txt
   py.test --pdb -s

Playing with websocket APIs
===========================

I find no easy way to write tests for websocket APIs, so if you're not sure about the behavior of those APIs, you can run a citadel instance and test them using `wsdump.py <https://github.com/websocket-client/websocket-client#usage>`_

.. sourcecode:: shell

   # initiate database
   ./shell.py
   > db.create_all()

   # start webserver
   gunicorn citadel.app:app -c gunicorn_config.py

   # start celery worker
   export C_FORCE_ROOT=true
   celery -A citadel.app:celery worker

   # rock and roll
   wsdump.py ws://0.0.0.0/api/action/build
   > {"appname":"test-app","sha":"3641acaa644f160bc6d3e9d5562bf4eccaaf1f9c"}

For ENJOY team
==============

.. sourcecode:: shell

   tools/deploy.sh test origin feature/next-gen
   ssh c1-eru-2 -t 'sudo su'
   workon citadel && cd /opt/citadel && py.test -s --pdb
