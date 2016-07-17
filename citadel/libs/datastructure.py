# coding: utf-8
from webargs import fields
from datetime import datetime

from werkzeug.routing import BaseConverter, ValidationError


class DateConverter(BaseConverter):
    """Extracts a ISO8601 date from the path and validates it."""

    regex = r'\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return value.strftime('%Y-%m-%d')


repo_field = fields.Str(required=True)
podname_field = fields.Str(required=True)
entrypoint_field = fields.Str(required=True)
cpu_field = fields.Float(required=True)
count_field = fields.Int(required=True)
sha_field = fields.Str(required=True)
artifact_field = fields.Str(missing='')
uid_field = fields.Str(missing='')
networks_field = fields.Dict(missing={})
envname_field = fields.Str(missing='')
extra_env_field = fields.List(fields.Str(), missing=[])
ids_field = fields.List(fields.Str(), missing=[])
appname_field = fields.Str(required=True)
git_field = fields.Str(required=True)
