# coding: utf-8
from .client import CoreRPC
from citadel.config import GRPC_ADDRESS


core = CoreRPC(GRPC_ADDRESS)
