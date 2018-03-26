# -*- coding: utf-8 -*-

import json
from datetime import datetime
from decimal import Decimal
from flask import Response
from functools import wraps
from google.protobuf.internal import api_implementation


if api_implementation.Type() == 'cpp':
    from google.protobuf.pyext.cpp_message import GeneratedProtocolMessageType
    from google.protobuf.pyext._message import ScalarMapContainer as ScalarMap
    from google.protobuf.pyext._message import RepeatedScalarContainer as RepeatedScalarFieldContainer
    from google.protobuf.pyext._message import RepeatedCompositeContainer as RepeatedCompositeFieldContainer
else:
    from google.protobuf.internal.python_message import GeneratedProtocolMessageType
    from google.protobuf.internal.containers import ScalarMap, RepeatedScalarFieldContainer, RepeatedCompositeFieldContainer


class Jsonized:

    _raw = {}

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __str__(self):
        return str(self.__dict__)

    def to_dict(self):
        return self._raw


class VersatileEncoder(json.JSONEncoder):

    def convert_grpc_types(self, obj):
        if isinstance(obj, ScalarMap):
            return dict(obj)
        if isinstance(obj, RepeatedScalarFieldContainer):
            return list(obj)
        if isinstance(type(obj), GeneratedProtocolMessageType):
            return self.default(obj)
        if isinstance(obj, RepeatedCompositeFieldContainer):
            return [self.default(o) for o in obj]
        return obj

    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        if isinstance(type(obj), GeneratedProtocolMessageType):
            field_names = [field.name for field in obj.DESCRIPTOR.fields]
            dic = {n: self.convert_grpc_types(getattr(obj, n)) for n in field_names}
            # need this to identify what kind of message is this
            dic['__class__'] = obj.__class__.__name__
            return dic
        return super(VersatileEncoder, self).default(obj)


def jsonize(f):
    @wraps(f)
    def _(*args, **kwargs):
        r = f(*args, **kwargs)
        data, code = r if isinstance(r, tuple) else (r, 200)
        try:
            return Response(json.dumps(data, cls=VersatileEncoder), status=code, mimetype='application/json')
        except TypeError:
            # data could be flask.Response objects, e.g. redirect responses
            return data
    return _
