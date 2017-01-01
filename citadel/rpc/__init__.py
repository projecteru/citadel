# -*- coding: utf-8 -*-
from .client import CoreRPC
from citadel.config import ZONE_CONFIG
from citadel.libs.utils import memoize


@memoize
def get_core(zone):
    grpc_url = ZONE_CONFIG[zone]['GRPC_URL']
    return CoreRPC(grpc_url)
