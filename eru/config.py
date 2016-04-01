import os


def get_env(name, default=None, force_type=None):
    """get value from os.environ, if not force_type, infer from default"""
    res = os.getenv(name, default)
    if force_type is not None:
        return force_type(res)
    if default is not None:
        return default.__class__(res)
    return res


ERU_BIND = get_env('ERU_BIND', '0.0.0.0:5000')
ERU_DAEMON = get_env('ERU_DAEMON', False)
ERU_OPLOG_PATH = get_env('ERU_OPLOG_PATH', '/tmp/op.log')
ERU_TIMEOUT = get_env('ERU_TIMEOUT', 300)
ERU_WORKERS = get_env('ERU_WORKERS', 4)
ERU_WORKER_CLASS = get_env('ERU_WORKER_CLASS', 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker')
ERU_AGENT_PORT = get_env('ERU_AGENT_PORT', 12345)

NETWORK_PROVIDER = get_env('NETWORK_PROVIDER', 'macvlan')

DOCKER_CERT_PATH = get_env('DOCKER_CERT_PATH', '')
DOCKER_REGISTRY = get_env('DOCKER_REGISTRY', 'docker-registry.intra.hunantv.com')
DOCKER_REGISTRY_URL = get_env('DOCKER_REGISTRY_URL', 'http://docker-registry.intra.hunantv.com')
DOCKER_REGISTRY_INSECURE = get_env('DOCKER_REGISTRY_INSECURE', False)
DOCKER_REGISTRY_USERNAME = get_env('DOCKER_REGISTRY_USERNAME', '')
DOCKER_REGISTRY_PASSWORD = get_env('DOCKER_REGISTRY_PASSWORD', '')
DOCKER_REGISTRY_EMAIL = get_env('DOCKER_REGISTRY_EMAIL', '')

DOCKER_LOG_DRIVER = get_env('DOCKER_LOG_DRIVER', 'none')
DOCKER_NETWORK_MODE = get_env('DOCKER_NETWORK_MODE', 'bridge')
DOCKER_NETWORK_DISABLED = get_env('DOCKER_NETWORK_DISABLED', False)

DEFAULT_CORE_SHARE = get_env('DEFAULT_CORE_SHARE', 10)
DEFAULT_MAX_SHARE_CORE = get_env('DEFAULT_MAX_SHARE_CORE', -1)

GIT_KEY_PUB = get_env('GIT_KEY_PUB', '')
GIT_KEY_PRI = get_env('GIT_KEY_PRI', '')
GIT_KEY_USER = get_env('GIT_KEY_USER', '')
GIT_KEY_ENCRYPT = get_env('GIT_KEY_ENCRYPT', '')
GIT_USERNAME = get_env('GIT_USERNAME', '')
GIT_PASSWORD = get_env('GIT_PASSWORD', '')

MYSQL_HOST = get_env('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = get_env('MYSQL_PORT', 3306)
MYSQL_USER = get_env('MYSQL_USER', 'eru')
MYSQL_PASSWORD = get_env('MYSQL_PASSWORD', '')
MYSQL_DATABASE = get_env('MYSQL_DATABASE', 'eru')

SQLALCHEMY_POOL_SIZE = get_env('SQLALCHEMY_POOL_SIZE', 100)
SQLALCHEMY_POOL_TIMEOUT = get_env('SQLALCHEMY_POOL_TIMEOUT', 3600)
SQLALCHEMY_POOL_RECYCLE = get_env('SQLALCHEMY_POOL_RECYCLE', 2000)

REDIS_HOST = get_env('REDIS_HOST', '127.0.0.1')
REDIS_PORT = get_env('REDIS_PORT', 6379)
REDIS_POOL_SIZE = get_env('REDIS_POOL_SIZE', 100)

ETCD = get_env('ETCD', '127.0.0.1:2379')

CELERY_ACCEPT_CONTENT = get_env('CELERY_ACCEPT_CONTENT', 'pickle,json,msgpack,yaml').split(',')
CELERY_ENABLE_UTC = get_env('CELERY_ENABLE_UTC', False)
CELERY_FORCE_ROOT = get_env('CELERY_FORCE_ROOT', False)
CELERY_REDIS_MAX_CONNECTIONS = get_env('CELERY_REDIS_MAX_CONNECTIONS', 1024)
CELERY_BROKER_URL = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_TASK_RESULT_EXPIRES = get_env('CELERY_TASK_RESULT_EXPIRES', 604800)
CELERY_TRACK_STARTED = get_env('CELERY_TRACK_STARTED', True)
CELERY_TIMEZONE = get_env('CELERY_TIMEZONE', 'Asia/Chongqing')
CELERY_SEND_TASK_ERROR_EMAILS = get_env('CELERY_SEND_TASK_ERROR_EMAILS', True)
CELERY_ADMINS = get_env('CELERY_ADMINS', '')

SERVER_EMAIL = get_env('SERVER_EMAIL', '')
EMAIL_HOST = get_env('EMAIL_HOST', '')
EMAIL_PORT = get_env('EMAIL_PORT', 465)
EMAIL_HOST_USER = get_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_SSL = get_env('EMAIL_USE_SSL', True)

ERU_HOST_PERMDIR = get_env('ERU_HOST_PERMDIR', '/mnt/mfs/permdirs/%s')
ERU_CONTAINER_PERMDIR = get_env('ERU_CONTAINER_PERMDIR', '/%s/permdir')

FALCON_API_HOST = get_env('FALCON_API_HOST', 'http://localhost')

try:
    from local_config import *
except ImportError:
    pass

SQLALCHEMY_DATABASE_URI = 'mysql://{0}:{1}@{2}:{3}/{4}'.format(MYSQL_USER,
                                                               MYSQL_PASSWORD,
                                                               MYSQL_HOST,
                                                               MYSQL_PORT,
                                                               MYSQL_DATABASE)
ADMINS = [line.split(':') for line in CELERY_ADMINS.split(',')]
