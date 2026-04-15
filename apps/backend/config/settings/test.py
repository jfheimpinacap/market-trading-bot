from .base import *  # noqa: F403, F401

DEBUG = False
ENVIRONMENT = 'test'

# Force a fully portable test database backend independent from local PostgreSQL.
# Supports override via DJANGO_TEST_DB_NAME when a file-backed SQLite DB is needed.
TEST_DB_NAME = get_env('DJANGO_TEST_DB_NAME', ':memory:')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': TEST_DB_NAME,
        'TEST': {
            'NAME': TEST_DB_NAME,
        },
    },
}

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
