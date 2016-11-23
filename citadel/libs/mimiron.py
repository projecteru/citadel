# coding: utf-8

from citadel.ext import rds
from citadel.libs.utils import logger


_MIMIRON_CONTAINER_KEY = 'mimiron:{}:route'
_MIMIRON_USER_KEY = 'mimiron:{}:list'


def set_mimiron_route(container_id, node, users):
    """
    因为删除容器的时候，拿不到 permitted_users，
    而我们又需要知道每个用户名下有那些容器，
    所以保存两个 redis key
    """
    container_key = _MIMIRON_CONTAINER_KEY.format(container_id)
    server = '{}:22'.format(node.ip)
    for user in users:
        user_key = _MIMIRON_USER_KEY.format(user)
        rds.hset(container_key, user, server)
        rds.sadd(user_key, container_id)
        logger.debug('Set mimiron route: container: %s, user: %s', container_key, user_key)


def del_mimiron_route(container_id):
    container_key = _MIMIRON_CONTAINER_KEY.format(container_id)
    if container_key not in rds:
        return

    pipeline = rds.pipeline()
    for user in rds.hkeys(container_key):
        user_key = _MIMIRON_USER_KEY.format(user)
        pipeline.srem(user_key, container_id)
    pipeline.delete(container_key)
    pipeline.execute()


def get_mimiron_containers_for_user(username):
    user_key = _MIMIRON_USER_KEY.format(username)
    return rds.smembers(user_key)
