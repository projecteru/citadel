from smart_getenv import getenv

# flask settings
DEBUG = getenv('DEBUG', default=False, type=bool)
SERVER_NAME = getenv('SERVER_NAME')

REDIS_HOST = getenv('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = getenv('REDIS_PORT', default=6379, type=int)
REDIS_POOL_SIZE = getenv('REDIS_POOL_SIZE', default=100, type=int)


# celery settings
SERVER_EMAIL = getenv('SERVER_EMAIL')
EMAIL_HOST = getenv('EMAIL_HOST', default='smtp.exmail.qq.com')
EMAIL_PORT = getenv('EMAIL_PORT', default=465, type=int)
EMAIL_HOST_USER = getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_SSL = getenv('EMAIL_USE_SSL', default=True, type=bool)
CELERY_ADMINS = getenv('CELERY_ADMINS', default='')
ADMINS = [line.split(':') for line in CELERY_ADMINS.split(',')]
CELERYD_MAX_TASKS_PER_CHILD = getenv('CELERYD_MAX_TASKS_PER_CHILD', default=100, type=int)
CELERY_SEND_TASK_ERROR_EMAILS = getenv('CELERY_SEND_TASK_ERROR_EMAILS', default=True, type=bool)
CELERY_TIMEZONE = getenv('CELERY_TIMEZONE', default='Asia/Chongqing')
CELERY_BROKER_URL = 'redis://{}:{}'.format(REDIS_HOST, REDIS_PORT)
CELERY_ENABLE_UTC = False
CELERY_DEFAULT_QUEUE = 'notbot'
CELERY_FORCE_ROOT = getenv('CELERY_FORCE_ROOT')
