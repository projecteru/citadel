# -*- coding: utf-8 -*-

import json

from citadel.libs.jsonutils import VersatileEncoder
from citadel.rpc.core_pb2 import Network, Node, BuildImageMessage, ErrorDetail, Pods, Pod


def test_encode_grpc_objects():
    error = ErrorDetail(code=42, message='shit, man')
    build_message = BuildImageMessage(
        id='whatever',
        error_detail=error,
    )
    json_string = json.dumps(build_message, cls=VersatileEncoder)
    reconstruct_obj = json.loads(json_string)
    assert reconstruct_obj == {
        'id': 'whatever',
        'status': '',
        'progress': '',
        'error': '',
        'stream': '',
        'error_detail': {
            'code': 42,
            'message': 'shit, man',
            '__class__': 'ErrorDetail',
        },
        '__class__': 'BuildImageMessage',
    }

    node = Node(name='whatever', cpu={'foo': 42}, labels={'foo': 'bar'})
    json_string = json.dumps(node, cls=VersatileEncoder)
    reconstruct_obj = json.loads(json_string)
    assert reconstruct_obj == {
        'name': 'whatever',
        'endpoint': '',
        'podname': '',
        'cpu': {'foo': 42},
        'memory': 0,
        'info': '',
        'available': False,
        'labels': {'foo': 'bar'},
        '__class__': 'Node',
    }

    network = Network(name='whatever', subnets=['foo', 'bar'])
    json_string = json.dumps(network, cls=VersatileEncoder)
    reconstruct_obj = json.loads(json_string)
    assert reconstruct_obj == {
        'name': 'whatever',
        'subnets': ['foo', 'bar'],
        '__class__': 'Network',
    }

    pod = Pod(name='whatever', desc='whatever')
    pods = Pods(pods=[pod, pod])
    json_string = json.dumps(list(pods.pods), cls=VersatileEncoder)
    reconstruct_obj = json.loads(json_string)
    assert len(reconstruct_obj) == 2
    assert reconstruct_obj[0] == {
        'name': 'whatever',
        'desc': 'whatever',
        '__class__': 'Pod',
    }
