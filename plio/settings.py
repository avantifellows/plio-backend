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
SECRET_KEY = os.environ["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ["DEBUG"]

ALLOWED_HOSTS = [
    "0.0.0.0",
    "127.0.0.1",
    "staging.plio.in",
    "backend.plio.in",
    "oix3vlacdg.execute-api.ap-south-1.amazonaws.com",  # Staging Lambda
    "musxsu7886.execute-api.ap-south-1.amazonaws.com",  # Prod Lambda
]

if "RDS_DB_NAME" in os.environ:
    SECURE_SSL_REDIRECT = True
else:
    SECURE_SSL_REDIRECT = False

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
    "django_s3_storage",
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
    "django_tenants.middleware.main.TenantMainMiddleware",
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
    "organizations.middleware.OrganizationTenantMiddleware",
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
CMS_TOKEN = os.environ["CMS_TOKEN"]
GET_CMS_PROBLEM_URL = "/problems"

DATABASES = {
    "default": {
        "ENGINE": os.environ["DB_ENGINE"],
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": int(os.environ["DB_PORT"]),
    }
}

AUTH_USER_MODEL = "users.User"

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

FRONTEND_URL = "https://app.plio.in"

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ["GOOGLE_OAUTH2_CLIENT_ID"]
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ["GOOGLE_OAUTH2_CLIENT_SECRET"]

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = os.environ["AWS_REGION"]

API_APPLICATION_NAME = "plio"

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 60 * 60 * 24,  # 1 day
    "DEFAULT_SCOPES": ["read", "write"],
}

OTP_EXPIRE_SECONDS = 300

CORS_ALLOW_HEADERS = list(default_headers) + [
    "organization",
]

DEFAULT_ROLES = [
    {"name": "super-admin"},
    {"name": "org-admin"},
    {"name": "org-view"},
]

CHANNEL_LAYERS = {
    "default": {
        # Method 1: Via redis lab
        # Method 2: Via local Redis
        # Method 3: Via In-memory channel layer
        # Using this method.
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}
