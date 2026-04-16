import hashlib
import os
from pathlib import Path
from environs import Env
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()
if not os.path.exists(".env"):
    print(".env not found, creating .env")
    exit(1)
env.read_env(path=BASE_DIR / ".env")

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG")
API_TOKEN = env.str("API_TOKEN")
ADMIN = env.str("ADMIN")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", 
    default=["5cd6-45-153-61-230.ngrok-free.app", "localhost", "127.0.0.1", "0.0.0.0"])
WEB_DOMAIN = env.str("WEB_DOMAIN")

print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")

WEBHOOK_PATH = 'bot/' + hashlib.md5(API_TOKEN.encode()).hexdigest()
WEBHOOK_URL = f"{WEB_DOMAIN}/{WEBHOOK_PATH}"

# Application definition

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.import_export',
    'unfold.contrib.inlines',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # DOWNLOAD
    'ckeditor',
    'tinymce',
    'import_export',
    'django_celery_beat',

    # LOCAL
    'common.apps.CommonConfig',
    'support.apps.SupportConfig',
    'quiz.apps.QuizConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    index = INSTALLED_APPS.index('import_export')
    INSTALLED_APPS.insert(index + 1, 'debug_toolbar')
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

if not DEBUG:
    index = INSTALLED_APPS.index('django.contrib.staticfiles')
    INSTALLED_APPS.insert(index, "whitenoise.runserver_nostatic")
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware", )

ROOT_URLCONF = 'src.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'src.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DB_SQLITE = 'sqlite'
DB_POSTGRESQL = 'postgresql'
PGBOUNCER = 'pgbouncer'

DB_ALL = {
    DB_SQLITE: {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    DB_POSTGRESQL: {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.str("DB_NAME"),
        'USER': env.str("DB_USER"),
        'PASSWORD': env.str("DB_PASSWORD"),
        'HOST': env.str("DB_HOST"),
        'PORT': env.str("DB_PORT"),
        'CONN_MAX_AGE': 20,
    },
    PGBOUNCER: {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str("DB_NAME"),
            'USER': env.str("DB_USER"),
            'PASSWORD': env.str("DB_PASSWORD"),
            'HOST': env.str("PGBOUNCER_HOST"),
            'PORT': env.str("PGBOUNCER_PORT"),
            "CONN_MAX_AGE": 0
        }
}

DATABASES = {
    "default": DB_ALL[env.str("DJANGO_DB", default=DB_SQLITE)]
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

if not DEBUG:
    STORAGES = {
        # ...
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "LOCATION": os.path.join(BASE_DIR, "media"),
        }
    }

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

REDIS_HOST = env.str("REDIS_HOST", "redis")
REDIS_PORT = env.int("REDIS_PORT", 6379)
REDIS_DB = env.int("REDIS_DB", 0)
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = env.str("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

CKEDITOR_CONFIGS = {
    'default': {
        'height': 300,
        'width': 350,
        'skin': 'moono',
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline', 'Link'],  # Основные инструменты
            ['Format', 'RemoveFormat'],  # Форматирование
        ],
        'allowedContent': True,  # Разрешить кастомные HTML-теги (см. ниже)
        'extraAllowedContent': 'a[!href];b;i;u;em;strong;blockquote',  # Разрешенные теги Telegram
    }
}

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_RESTRICT_BY_USER = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INTERNAL_IPS = ["127.0.0.1"]

UNFOLD = {
    "SITE_TITLE": "Manager Quiz",
    "SITE_HEADER": "Manager Quiz | Bot",
    "SITE_SYMBOL": "quiz",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "238 242 255",
            "100": "224 231 255",
            "200": "199 210 254",
            "300": "165 180 252",
            "400": "129 140 248",
            "500": "99 102 241",
            "600": "79 70 229",
            "700": "67 56 202",
            "800": "55 48 163",
            "900": "49 46 129",
            "950": "30 27 75",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("General"),
                "separator": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Users"),
                "separator": True,
                "items": [
                    {
                        "title": _("Auth Users"),
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": _("Auth Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("Telegram Profiles"),
                        "icon": "person",
                        "link": reverse_lazy("admin:common_telegramprofile_changelist"),
                        "badge": "dashboard.badge_new_users",
                    },
                ],
            },
            {
                "title": _("Quiz"),
                "separator": True,
                "items": [
                    {
                        "title": _("Categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:quiz_category_changelist"),
                    },
                    {
                        "title": _("Pending Categories"),
                        "icon": "pending",
                        "link": reverse_lazy("admin:quiz_categorypending_changelist"),
                    },
                    {
                        "title": _("Quizzes"),
                        "icon": "quiz",
                        "link": reverse_lazy("admin:quiz_quiz_changelist"),
                    },
                    {
                        "title": _("Quiz Parts"),
                        "icon": "article",
                        "link": reverse_lazy("admin:quiz_quizpart_changelist"),
                    },
                    {
                        "title": _("Questions"),
                        "icon": "help",
                        "link": reverse_lazy("admin:quiz_question_changelist"),
                    },
                ],
            },
            {
                "title": _("Sessions"),
                "separator": True,
                "items": [
                    {
                        "title": _("User Quizzes"),
                        "icon": "history_edu",
                        "link": reverse_lazy("admin:quiz_userquiz_changelist"),
                    },
                    {
                        "title": _("Group Quizzes"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:quiz_groupquiz_changelist"),
                    },
                ],
            },
            {
                "title": _("Bot"),
                "separator": True,
                "items": [
                    {
                        "title": _("Bot Commands"),
                        "icon": "terminal",
                        "link": reverse_lazy("admin:quiz_telegramcommand_changelist"),
                    },
                    {
                        "title": _("Bot Data"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:common_data_changelist"),
                    },
                ],
            },
            {
                "title": _("Support"),
                "separator": True,
                "items": [
                    {
                        "title": _("Support Messages"),
                        "icon": "support_agent",
                        "link": reverse_lazy("admin:support_supportmessage_changelist"),
                        "badge": "dashboard.badge_pending_support",
                    },
                ],
            },
            {
                "title": _("Celery"),
                "separator": True,
                "items": [
                    {
                        "title": _("Periodic Tasks"),
                        "icon": "schedule",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                    {
                        "title": _("Crontab Schedules"),
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:django_celery_beat_crontabschedule_changelist"),
                    },
                    {
                        "title": _("Interval Schedules"),
                        "icon": "timer",
                        "link": reverse_lazy("admin:django_celery_beat_intervalschedule_changelist"),
                    },
                ],
            },
        ],
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
}
