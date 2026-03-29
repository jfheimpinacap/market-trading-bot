import importlib.util
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MONOREPO_ROOT = BASE_DIR.parents[1]


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(BASE_DIR / '.env')


def get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def get_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default[:] if default else []
    return [item.strip() for item in value.split(',') if item.strip()]


SECRET_KEY = get_env('DJANGO_SECRET_KEY', 'change-me')
DEBUG = get_bool('DJANGO_DEBUG', default=False)
ENVIRONMENT = get_env('DJANGO_ENV', 'local')
APP_MODE = get_env('APP_MODE', 'full')
ALLOWED_HOSTS = get_list('DJANGO_ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
]

if importlib.util.find_spec('corsheaders') is not None:
    THIRD_PARTY_APPS.insert(0, 'corsheaders')

LOCAL_APPS = [
    'apps.common',
    'apps.health',
    'apps.markets',
    'apps.paper_trading',
    'apps.execution_simulator',
    'apps.risk_demo',
    'apps.risk_agent',
    'apps.position_manager',
    'apps.signals',
    'apps.postmortem_demo',
    'apps.postmortem_agents',
    'apps.agents',
    'apps.audit',
    'apps.automation_demo',
    'apps.policy_engine',
    'apps.proposal_engine',
    'apps.semi_auto_demo',
    'apps.continuous_demo',
    'apps.safety_guard',
    'apps.evaluation_lab',
    'apps.learning_memory',
    'apps.real_data_sync',
    'apps.real_market_ops',
    'apps.allocation_engine',
    'apps.operator_queue',
    'apps.replay_lab',
    'apps.experiment_lab',
    'apps.readiness_lab',
    'apps.runtime_governor',
    'apps.operator_alerts',
    'apps.notification_center',
    'apps.llm_local',
    'apps.research_agent',
    'apps.prediction_agent',
    'apps.prediction_training',
    'apps.opportunity_supervisor',
    'apps.mission_control',
    'apps.portfolio_governor',
    'apps.profile_manager',
    'apps.champion_challenger',
    'apps.memory_retrieval',
    'apps.promotion_committee',
    'apps.rollout_manager',
    'apps.incident_commander',
    'apps.chaos_lab',
    'apps.certification_board',
    'apps.broker_bridge',
    'apps.go_live_gate',
    'apps.execution_venue',
    'apps.venue_account',
    'apps.connector_lab',
    'apps.trace_explorer',
    'apps.runbook_engine',
    'apps.automation_policy',
    'apps.approval_center',
    'apps.trust_calibration',
    'apps.policy_tuning',
    'apps.policy_rollout',
    'apps.autonomy_manager',
    'apps.autonomy_rollout',
    'apps.autonomy_roadmap',
    'apps.autonomy_scenario',
    'apps.autonomy_campaign',
    'apps.autonomy_program',
    'apps.autonomy_scheduler',
    'apps.autonomy_launch',
    'apps.autonomy_activation',
    'apps.autonomy_operations',
    'apps.autonomy_intervention',
    'apps.autonomy_recovery',
    'apps.autonomy_disposition',
    'apps.autonomy_closeout',
    'apps.autonomy_followup',
    'apps.autonomy_feedback',
    'apps.autonomy_insights',
    'apps.autonomy_advisory',
    'apps.autonomy_advisory_resolution',
    'apps.autonomy_backlog',
    'apps.autonomy_intake',
    'apps.autonomy_planning_review',
    'apps.autonomy_decision',
    'apps.autonomy_package',
    'apps.autonomy_package_review',
    'apps.autonomy_seed',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if importlib.util.find_spec('corsheaders') is not None:
    MIDDLEWARE.insert(1, 'corsheaders.middleware.CorsMiddleware')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': get_env('DJANGO_DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': get_env('POSTGRES_DB', get_env('DJANGO_DB_NAME', 'market_trading_bot')),
        'USER': get_env('POSTGRES_USER', get_env('DJANGO_DB_USER', 'market_user')),
        'PASSWORD': get_env('POSTGRES_PASSWORD', get_env('DJANGO_DB_PASSWORD', 'market_password')),
        'HOST': get_env('POSTGRES_HOST', get_env('DJANGO_DB_HOST', 'localhost')),
        'PORT': get_env('POSTGRES_PORT', get_env('DJANGO_DB_PORT', '5432')),
    },
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = get_env('DJANGO_TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

CORS_ALLOWED_ORIGINS = get_list(
    'DJANGO_CORS_ALLOWED_ORIGINS',
    default=[
        'http://127.0.0.1:5173',
        'http://localhost:5173',
        'http://127.0.0.1:4173',
        'http://localhost:4173',
    ],
)

REDIS_URL = get_env('REDIS_URL', 'redis://localhost:6379/0')
REDIS_REQUIRED = get_bool('REDIS_REQUIRED', default=True)
CELERY_BROKER_URL = get_env('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = get_env('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_TIMEZONE = TIME_ZONE

LLM_ENABLED = get_bool('LLM_ENABLED', default=False)
LLM_PROVIDER = get_env('LLM_PROVIDER', 'ollama')
OLLAMA_BASE_URL = get_env('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_CHAT_MODEL = get_env('OLLAMA_CHAT_MODEL', 'llama3.2:3b')
OLLAMA_EMBED_MODEL = get_env('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
OLLAMA_TIMEOUT_SECONDS = int(get_env('OLLAMA_TIMEOUT_SECONDS', '30'))
