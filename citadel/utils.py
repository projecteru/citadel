from functools import wraps
from webargs import ValidationError

from flask import jsonify


def jsonize(f):
    @wraps(f)
    def _(*args, **kwargs):
        r = f(*args, **kwargs)
        data, code = r if isinstance(r, tuple) else (r, 200)
        return jsonify(data)
    return _


def require_one_of(*field_groups):
    """one of each group must be present"""
    def checker(args):
        for fields in field_groups:
            fields_ok = any(
                field in args and bool(args[field])
                for field in fields
            )
            if not fields_ok:
                raise ValidationError(
                    'Missing one of the required fields: {}'.format(fields)
                )

    return checker
