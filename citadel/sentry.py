# coding: utf-8

from flask.signals import got_request_exception, request_finished
from raven.conf import setup_logging
from raven.contrib.flask import Sentry, make_client
from raven.handlers.logging import SentryHandler


class SentryCollector(Sentry):

    def init_app(self, app, dsn=None, logging=None, level=None,
                 logging_exclusions=None, wrap_wsgi=None,
                 register_signal=None):
        if dsn is not None:
            self.dsn = dsn

        if level is not None:
            self.level = level

        if register_signal is not None:
            self.register_signal = register_signal

        if logging is not None:
            self.logging = logging

        if logging_exclusions is not None:
            self.logging_exclusions = logging_exclusions

        if not self.client:
            self.client = make_client(self.client_cls, app, self.dsn)

        if self.logging:
            kwargs = {}
            if self.logging_exclusions is not None:
                kwargs['exclude'] = self.logging_exclusions

            setup_logging(SentryHandler(self.client, level=self.level), **kwargs)

        app.before_request(self.before_request)

        if self.register_signal:
            got_request_exception.connect(self.handle_exception, sender=app)
            request_finished.connect(self.after_request, sender=app)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['sentry'] = self
