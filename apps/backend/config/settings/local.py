from .base import *  # noqa: F403, F401

DEBUG = get_bool('DJANGO_DEBUG', default=True)
ENVIRONMENT = 'local'
APP_MODE = get_env('APP_MODE', 'full')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
