from .base import *  # noqa: F403, F401

DEBUG = get_bool('DJANGO_DEBUG', default=True)
ENVIRONMENT = 'lite'
APP_MODE = 'lite'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.lite.sqlite3',
    },
}

REDIS_URL = ''
REDIS_REQUIRED = False
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
