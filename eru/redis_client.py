# coding: utf-8
import redis

from eru.config import REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE
from eru.storage.redis import RedisStorage


def get_redis_client(host, port , max_connections):
    pool = redis.ConnectionPool(host=host, port=port, max_connections=max_connections)
    return redis.Redis(connection_pool=pool)


rds = get_redis_client(REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE)
config_backend = RedisStorage(rds)
