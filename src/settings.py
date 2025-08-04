import hashlib
import os
from pathlib import Path
from environs import Env

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
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
WEB_DOMAIN = env.str("WEB_DOMAIN")

WEBHOOK_PATH = 'bot/' + hashlib.md5(API_TOKEN.encode()).hexdigest()
WEBHOOK_URL = f"{WEB_DOMAIN}/{WEBHOOK_PATH}"

# Application definition

INSTALLED_APPS = [
    'jazzmin',
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
    'adservice.apps.AdserviceConfig',
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
STATIC_ROOT = BASE_DIR / 'static'

if not DEBUG:
    STORAGES = {
        # ...
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
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
REDIS_URL = f'{REDIS_HOST}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

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
CSRF_TRUSTED_ORIGINS = [
    env.str("WEB_DOMAIN")
]

INTERNAL_IPS = ["127.0.0.1"]

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Manager Quiz | Bot",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Manager Quiz | Bot",

    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_brand": "Manager Quiz | Bot",

    # Logo to use for your site, must be present in static files, used for brand on top left
    "site_logo": "images/manager_quiz.jpg",

    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
    "login_logo": "images/manager_quiz.jpg",

    # Logo to use for login form in dark themes (defaults to login_logo)
    "login_logo_dark": None,

    # CSS classes that are applied to the logo above
    "site_logo_classes": "rounded-pill",

    # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)
    "site_icon": None,

    # Welcome text on the login screen
    "welcome_sign": "Welcome to the ManagerQuiz Bot Admin Panel",

    # Copyright on the footer
    "copyright": "Acme Library Ltd",

    # List of model admins to search from the search bar, search bar omitted if excluded
    # If you want to use a single search field you dont need to use a list, you can use a simple string
    "search_model": ["quiz.Quiz", "quiz.Category"],

    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": None,

    ############
    # Top Menu #
    ############

    # Links to put along the top menu
    "topmenu_links": [

        # Url that gets reversed (Permissions can be added)
        {
            "name": "Home",
            "url": "admin:index",
            "icon": "fas fa-chart-line",
            "permissions": ["auth.view_user"]
        },

        # external url that opens in a new window (Permissions can be added)
        # {"name": "Аналитика", "url": "admin-analytics", "new_window": False},

        # model admin to link to (Permissions checked against model)
        # {"model": "auth.User"},

        # App with dropdown menu to all its models pages (Permissions checked against models)
        {"app": "common"},
        {"app": "quiz"},
        {"app": "support"},
    ],

    #############
    # User Menu #
    #############

    # Additional links to include in the user menu on the top right ("app" url type is not allowed)
    # "usermenu_links": [
    #     {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
    #     {"model": "responder.TelegramUser"}
    # ],

    #############
    # Side Menu #
    #############

    # Whether to display the side menu
    "show_sidebar": True,

    # Whether to aut expand the menu
    "navigation_expanded": True,

    # Hide these apps when generating side menu e.g (auth)
    "hide_apps": [],

    # Hide these models when generating side menu (e.g auth.user)
    "hide_models": [
        # 'django_celery_beat.SolarSchedule',
        # 'django_celery_beat.IntervalSchedule',
        # 'django_celery_beat.TzAwareCrontab',
        # 'django_celery_beat.ClockedSchedule',
    ],

    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": [
        "auth",

        "common",
        "common.TelegramProfile",
        "common.Language",
        "common.Text",
        "common.TextCode",
        "common.Data",

        "quiz",
        "quiz.Category",
        "quiz.CategoryPending",
        "quiz.Quiz",
        "quiz.QuizPart",
        "quiz.Question",
        "quiz.Option",
        "quiz.UserQuiz",
        "quiz.GroupQuiz",
        "quiz.TelegramCommand",

        "support",
        "support.SupportMessage",
    ],

    "icons": {
        "admin:index": "fas fa-gauge",

        "auth": "fas fa-users-cog",
        "auth.User": "fas fa-user-tie",
        "auth.Permission": "fas fa-key",
        "auth.Group": "fas fa-users",

        "common.TelegramProfile": "fas fa-user",
        "common.Language": "fas fa-language",
        "common.Text": "fas fa-font",
        "common.TextCode": "fas fa-barcode",
        "common.Data": "fas fa-toolbox",

        "quiz.Category": "fas fa-list",
        "quiz.CategoryPending": "fas fa-thin fa-list",
        "quiz.Quiz": "fas fa-square-poll-vertical",
        "quiz.QuizPart": "fas fa-quote-right",
        "quiz.Question": "fas fa-circle-question",
        "quiz.Option": "fas fa-comments",
        "quiz.UserQuiz": "fas fa-solid fa-book-journal-whills",
        "quiz.GroupQuiz": "fas fa-book",
        "quiz.TelegramCommand": "fas fa-terminal",

        "support.SupportMessage": "fas fa-info",

        "admin.LogEntry": "fas fa-file-pen",
        "contenttypes.ContentType": "fas fa-keyboard",

        "django_celery_beat.PeriodicTask": "fas fa-clock",
        "django_celery_beat.IntervalSchedule": "fas fa-stopwatch",
        "django_celery_beat.CrontabSchedule": "fas fa-calendar-alt",
        "django_celery_beat.SolarSchedule": "fas fa-sun",
        "django_celery_beat.ClockedSchedule": "fas fa-clock",
        "django_celery_beat.PeriodicTasks": "fas fa-tasks",

        "sessions.Session": "fas fa-user-clock",

    },
    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    #################
    # Related Modal #
    #################
    # Use modals instead of popups
    "related_modal_active": True,

    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in static files)
    "custom_css": None,
    "custom_js": None,
    # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)
    "use_google_fonts_cdn": True,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": True,

    ###############
    # Change view #
    ###############
    # Render out the change view as a single form, or in tabs, current options are
    # - single
    # - horizontal_tabs (default)
    # - vertical_tabs
    # - collapsible
    # - carousel
    "changeform_format": "horizontal_tabs",
    # override change forms on a per modeladmin basis
    # "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
    # Add a language dropdown into the admin
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-info",
    "accent": "accent-info",
    "navbar": "navbar-info navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-info",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "united",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-outline-success"
    }
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
