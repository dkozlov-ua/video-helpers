"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
from pathlib import Path

import environ
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from backend.utils import generate_secret_key

# Initialize env vars parser
# https://django-environ.readthedocs.io/en/latest/
env = environ.Env()

# Initialize Sentry SDK
# https://docs.sentry.io/platforms/python/guides/django/
# https://docs.sentry.io/platforms/python/guides/celery/
sentry_sdk.init(
    integrations=[
        CeleryIntegration(),
        DjangoIntegration(),
    ],
    traces_sample_rate=1.0,
    send_default_pii=True,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default=generate_secret_key())

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

DATABASES = {
    'default': {
        'CONN_MAX_AGE': 0,
        **env.db_url('DATABASE_URL', default='psql://postgres:postgres@postgres:5432/postgres'),
    },
}

# Application definition
INSTALLED_APPS = [
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'moviemaker',
    'telegram',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        }
    }
]

WSGI_APPLICATION = 'backend.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_ROOT = env.path('MEDIA_ROOT', default=BASE_DIR / 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery settings
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_EVENT_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_ACCEPT_CONTENT = ['pickle']
CELERY_IGNORE_RESULT = False
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-videos': {
        'task': 'moviemaker.tasks.cleanup_old_videos',
        'schedule': 3600.0,
    },
}

# Telegram settings
TELEGRAM_BOT_ENABLED = env.bool('TELEGRAM_BOT_ENABLED', default=False)
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='TELEGRAM_BOT_TOKEN_NOTSET')

# Grappelli settings
# https://django-grappelli.readthedocs.io/en/latest
GRAPPELLI_ADMIN_TITLE = 'Movie Maker'

# Youtube-dl settings
YOUTUBE_VIDEO_FORMAT = env('YOUTUBE_VIDEO_FORMAT', default='bestvideo[height<=720]+bestaudio/best[height<=720]')
YOUTUBE_RATE_LIMIT = env('YOUTUBE_RATE_LIMIT', default=None)

# MoviePy settings
# https://zulko.github.io/moviepy
VIDEO_FINAL_OUTPUT_FORMAT = 'webm'
VIDEO_FINAL_ENCODER_SETTINGS = {
    'threads': 1,
}
VIDEO_TEMP_OUTPUT_FORMAT = 'mp4'
VIDEO_TEMP_ENCODER_SETTINGS = {
    'preset': 'veryfast',
    # 'codec': 'libx264',
    # 'bitrate': '700K',
    'threads': 1,
}
