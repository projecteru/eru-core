import os

DEBUG = bool(os.getenv('DEBUG', ''))
ERU_BIND = os.getenv('ERU_BIND', '0.0.0.0:5000')
ERU_DAEMON = bool(os.getenv('ERU_DAEMON', ''))
ERU_OPLOG_PATH = os.getenv('ERU_OPLOG_PATH', '/var/log/eru/op.log')
ERU_TIMEOUT = int(os.getenv('ERU_TIMEOUT', '300'))
ERU_WORKERS = int(os.getenv('ERU_WORKERS', '4'))
ERU_WORKER_CLASS = os.getenv('ERU_WORKER_CLASS', 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker')

DOCKER_CERT_PATH = os.getenv('DOCKER_CERT_PATH', '')
DOCKER_REGISTRY = os.getenv('DOCKER_REGISTRY', 'docker-registry.intra.hunantv.com')
DOCKER_REGISTRY_URL = os.getenv('DOCKER_REGISTRY_URL', 'http://docker-registry.intra.hunantv.com')
DOCKER_REGISTRY_INSECURE = bool(os.getenv('DOCKER_REGISTRY_INSECURE', ''))
DOCKER_REGISTRY_USERNAME = os.getenv('DOCKER_REGISTRY_USERNAME', '')
DOCKER_REGISTRY_PASSWORD = os.getenv('DOCKER_REGISTRY_PASSWORD', '')
DOCKER_REGISTRY_EMAIL = os.getenv('DOCKER_REGISTRY_EMAIL', '')

DOCKER_LOG_DRIVER = os.getenv('DOCKER_LOG_DRIVER', 'json-file')
DOCKER_NETWORK_MODE = os.getenv('DOCKER_NETWORK_MODE', 'bridge')
DOCKER_NETWORK_DISABLED = bool(os.getenv('DOCKER_NETWORK_DISABLED', ''))

DEFAULT_CORE_SHARE = int(os.getenv('DEFAULT_CORE_SHARE', '1'))
DEFAULT_MAX_SHARE_CORE = int(os.getenv('DEFAULT_MAX_SHARE_CORE', '-1'))

MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'eru')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'eru')

SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', '100'))
SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('SQLALCHEMY_POOL_TIMEOUT', '3600'))
SQLALCHEMY_POOL_RECYCLE = int(os.getenv('SQLALCHEMY_POOL_RECYCLE', '2000'))

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_POOL_SIZE = int(os.getenv('REDIS_POOL_SIZE', '100'))

CELERY_ACCEPT_CONTENT = os.getenv('CELERY_ACCEPT_CONTENT', 'pickle,json,msgpack,yaml').split(',')
CELERY_ENABLE_UTC = bool(os.getenv('CELERY_ENABLE_UTC', ''))
CELERY_FORCE_ROOT = bool(os.getenv('CELERY_FORCE_ROOT', ''))
CELERY_REDIS_MAX_CONNECTIONS = int(os.getenv('CELERY_REDIS_MAX_CONNECTIONS', '1024'))
CELERY_BROKER_URL = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_TASK_RESULT_EXPIRES = int(os.getenv('CELERY_TASK_RESULT_EXPIRES', '604800'))
CELERY_TRACK_STARTED = bool(os.getenv('CELERY_TRACK_STARTED', '1'))
CELERY_TIMEZONE = os.getenv('CELERY_TIMEZONE', 'Asia/Chongqing')
CELERY_SEND_TASK_ERROR_EMAILS = bool(os.getenv('CELERY_SEND_TASK_ERROR_EMAILS', '1'))
CELERY_ADMINS = os.getenv('CELERY_ADMINS', '')

SERVER_EMAIL = os.getenv('SERVER_EMAIL', '')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_SSL = bool(os.getenv('EMAIL_USE_SSL', '1'))

ERU_HOST_PERMDIR = os.getenv('ERU_HOST_PERMDIR', '/mnt/mfs/permdirs/%s')
ERU_CONTAINER_PERMDIR = os.getenv('ERU_CONTAINER_PERMDIR', '/%s/permdir')

try:
    from local_config import *
except ImportError:
    pass

SQLALCHEMY_DATABASE_URI = 'mysql://{0}:{1}@{2}:{3}/{4}'.format(MYSQL_USER,
        MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE)
ADMINS = [line.split(':') for line in CELERY_ADMINS.split(',')]
