# coding: utf-8

from citadel.config import GRPC_HOST, GRPC_PORT
from .client import CoreRPC


core = CoreRPC(GRPC_HOST, GRPC_PORT)
