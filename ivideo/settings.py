"""
Django settings for ivideo project.

Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import logging
import json

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+o3e(i8els(3bv43!4^lflht9p9l#b%$wa+p4fmb$h#xa))%5u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
                '0.0.0.0', 
                '127.0.0.1', 
                'ivideo.eba-ra9p3ies.ap-south-1.elasticbeanstalk.com', 
                'staging.plio.in', 
                'ivideo.plio.in', 
                'oix3vlacdg.execute-api.ap-south-1.amazonaws.com', # Staging Lambda
                'musxsu7886.execute-api.ap-south-1.amazonaws.com' # Prod Lambda
                ]

if 'RDS_DB_NAME' in os.environ:
    SECURE_SSL_REDIRECT = True
else:
    SECURE_SSL_REDIRECT = False

# Application definition

INSTALLED_APPS = [
    'ivideo_player.apps.IvideoPlayerConfig',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_s3_storage'
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'UNAUTHENTICATED_USER': None,
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'request_logging.middleware.LoggingMiddleware'
]

ROOT_URLCONF = 'ivideo.urls'

CORS_ALLOW_ALL_ORIGINS = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
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


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
LOGGER_FILE = os.path.join('/tmp/all.log')

REQUEST_LOGGING_DATA_LOG_LEVEL = logging.DEBUG

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOGGER_FILE,
            'formatter': 'verbose'
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
            'formatter': 'verbose'
        }
    },
}

WSGI_APPLICATION = 'ivideo.wsgi.application'




# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
if 'DJANGO_ENV' in os.environ:
    json_data = open('zappa_settings.json')
    if os.environ['DJANGO_ENV'] == 'local':
        env_vars = json.load(json_data)['dev']['environment_variables']
    elif os.environ['DJANGO_ENV'] == 'prod':
        env_vars = json.load(json_data)['prod']['environment_variables']
    else:
        env_vars = json.load(json_data)['dev']['environment_variables']
    for key, val in env_vars.items():
        os.environ[key] = val


# The AWS region to connect to.
AWS_REGION = "ap-south-1"

# The AWS access key to use.
AWS_ACCESS_KEY_ID = "AKIARUBOPCTSWO57EU4K"

# The AWS secret access key to use.
AWS_SECRET_ACCESS_KEY = "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"

DEFAULT_FILE_STORAGE = "django_s3_storage.storage.S3Storage"
STATICFILES_STORAGE = "django_s3_storage.storage.StaticS3Storage"

# From AF S3 account
AWS_S3_PUBLIC_URL = "d3onnhzpzthjtl.cloudfront.net"
AWS_S3_BUCKET_NAME_STATIC = "plio-static"

# Depending on environment.
AWS_S3_KEY_PREFIX_STATIC = os.environ.get("STATIC_BUCKET")
AWS_S3_BUCKET_AUTH = False

AWS_S3_MAX_AGE_SECONDS = 60 * 60 * 24 * 365  # 1 year

STATIC_URL = f'{AWS_S3_PUBLIC_URL}/{AWS_S3_KEY_PREFIX_STATIC}/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'ivideo', 'static')
]