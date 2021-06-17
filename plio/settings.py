"""
Django settings for plio project.

Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import logging
from corsheaders.defaults import default_headers

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# App environment. Possible values are: local, staging, production
APP_ENV = os.environ.get("APP_ENV", "production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", False)

# allowed hosts that can access the Django app
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(" ")

# Application definition

SHARED_APPS = (
    "django_tenants",
    "users",
    "organizations",
    "plio",
    "experiments",
    "tags",
    "entries",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "oauth2_provider",
    "social_django",
    "rest_framework_social_oauth2",
)

TENANT_APPS = (
    "django.contrib.contenttypes",
    "rest_framework",
    "plio",
    "experiments",
    "tags",
    "entries",
)

INSTALLED_APPS = [
    "channels",
    "django_tenants",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_yasg",
    "safedelete",
    "users",
    "plio",
    "organizations",
    "experiments",
    "tags",
    "entries",
    "oauth2_provider",
    "social_django",
    "rest_framework_social_oauth2",
    "storages",
]

TENANT_MODEL = "organizations.Organization"
TENANT_DOMAIN_MODEL = "organizations.Domain"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework_social_oauth2.authentication.SocialAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
}

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "rest_framework_social_oauth2.backends.DjangoOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

MIDDLEWARE = [
    "organizations.middleware.OrganizationTenantMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "request_logging.middleware.LoggingMiddleware",
]

ROOT_URLCONF = "plio.urls"

CORS_ALLOW_ALL_ORIGINS = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
LOGGER_FILE = os.path.join("/tmp/all.log")

REQUEST_LOGGING_DATA_LOG_LEVEL = logging.DEBUG

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOGGER_FILE,
            "formatter": "verbose",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
            "formatter": "verbose",
        }
    },
}

WSGI_APPLICATION = "plio.wsgi.application"
ASGI_APPLICATION = "plio.asgi.application"


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_ROOT = os.path.join(BASE_DIR, "static/")

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "plio", "static"),
]

CMS_URL = "https://cms.peerlearning.com/api"
CMS_TOKEN = os.environ.get("CMS_TOKEN")
GET_CMS_PROBLEM_URL = "/problems"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django_tenants.postgresql_backend"),
        "NAME": os.environ.get("DB_NAME", "plio"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": int(os.environ.get("DB_PORT", 5432)),
    }
}

AUTH_USER_MODEL = "users.User"

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

FRONTEND_URL = "https://app.plio.in"

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get("GOOGLE_OAUTH2_CLIENT_ID", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get("GOOGLE_OAUTH2_CLIENT_SECRET", "")

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.environ.get("AWS_REGION", "")

DEFAULT_TENANT_SHORTCODE = os.environ.get("DEFAULT_TENANT_SHORTCODE", "")

API_APPLICATION_NAME = "plio"

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 60 * 60 * 24,  # 1 day
    "DEFAULT_SCOPES": ["read", "write"],
}

OTP_EXPIRE_SECONDS = 300  # 5 minutes

CORS_ALLOW_HEADERS = list(default_headers) + [
    "organization",
]

DEFAULT_ROLES = [
    {"name": "super-admin"},
    {"name": "org-admin"},
    {"name": "org-view"},
]

REDIS_HOSTNAME = os.environ.get("REDIS_HOSTNAME")
REDIS_PORT = os.environ.get("REDIS_PORT")

# https://channels.readthedocs.io/en/latest/topics/channel_layers.html
CHANNEL_LAYERS = {
    "default": {
        # using redis as the backing store
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(REDIS_HOSTNAME, REDIS_PORT)]},
    }
}

# authentication
ANALYTICS_IDP = {
    "type": os.environ.get("ANALYTICS_IDP_TYPE"),
    "token_url": os.environ.get("ANALYTICS_IDP_TOKEN_URL"),
    "client_id": os.environ.get("ANALYTICS_IDP_CLIENT_ID"),
    "client_secret": os.environ.get("ANALYTICS_IDP_CLIENT_SECRET"),
    "audience": os.environ.get("ANALYTICS_IDP_AUDIENCE", ""),
}

# email
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND")
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")

SMS_DRIVER = os.environ.get("SMS_DRIVER")

# file storage for uploaded images
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_QUERYSTRING_AUTH = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 mb

BIGQUERY = {
    "enabled": os.environ.get("BIGQUERY_ENABLED", APP_ENV in ["staging", "production"]),
    "project_id": os.environ.get("BIGQUERY_PROJECT_ID"),
    "location": os.environ.get("BIGQUERY_LOCATION"),
    "credentials_json_s3_bucket": os.environ.get("BIGQUERY_CREDENTIALS_JSON_S3_BUCKET"),
    "credentials_json_s3_filepath": os.environ.get(
        "BIGQUERY_CREDENTIALS_JSON_S3_FILEPATH"
    ),
}
