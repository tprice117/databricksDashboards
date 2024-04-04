"""
Django settings for api_proxy project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
import sys
from pathlib import Path

import dj_database_url
import environ
from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load our environment variables from the .env file
env = environ.Env(
    DEBUG=(bool, False),
    USE_I18N=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")

ENVIRONMENT = os.getenv("ENV")
DEBUG = os.getenv("ENV") == "TEST"
DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    # START:  Django Admin Interface
    "admin_interface",
    "colorfield",
    # END:  Django Admin Interface
    "django.contrib.admin",
    "django.contrib.auth",
    "mozilla_django_oidc",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    # START: Django Apps.
    "api",
    "payment_methods",
    "notifications",
    "billing",
    "communications",
    # END: Django Apps.
    "api.pricing_ml",
    "api.utils",
    "django_filters",
    "drf_spectacular",
    "django_extensions",
    "django_apscheduler",
    # START:  Django Humanize (for template number formatting).
    "django.contrib.humanize",
    # END:  Django Humanize (for template number formatting).
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]

ROOT_URLCONF = "api_proxy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            str(BASE_DIR) + "/templates/",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "api_proxy.wsgi.application"

# Add 'mozilla_django_oidc' authentication backend
AUTHENTICATION_BACKENDS = ("mozilla_django_oidc.auth.OIDCAuthenticationBackend",)

LOGIN_REDIRECT_URL = "admin:index"
LOGOUT_REDIRECT_URL = "admin:index"

# Database.
if ENVIRONMENT == "TEST":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "defaultdb",
            "USER": "doadmin",
            "PASSWORD": env("DB_PROD_PASSWORD"),
            "HOST": "db-postgresql-nyc1-05939-do-user-13480306-0.b.db.ondigitalocean.com",
            "PORT": "25060",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "defaultdb",
            "USER": "doadmin",
            "PASSWORD": env("DB_DEV_PASSWORD"),
            "HOST": "db-postgresql-nyc1-22939-do-user-13480306-0.b.db.ondigitalocean.com",
            "PORT": "25060",
        }
    }

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Add these new lines
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# Add machine learning models
ML_MODELS = os.path.join(BASE_DIR, "api/pricing_ml")

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

# DEFAULT_AUTO_FIELD = 'django.db.models.TextField'

CORS_ORIGIN_ALLOW_ALL = True
# CORS_ORIGIN_WHITELIST = [
#      'http://localhost:3000',
#      'http://localhost:62964',
# ]

# DRF Spectacular settings.
SPECTACULAR_SETTINGS = {
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "TITLE": "Downstream API",
    "DESCRIPTION": "Downstream API for the Downstream Market Network.",
    "VERSION": "1.0.0",
}

# Amazon Web Services S3 Configuration.
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION_NAME = "us-east-2"
AWS_S3_SIGNATURE_VERSION = "s3v4"
if ENVIRONMENT == "TEST":
    DEFAULT_FILE_STORAGE = "api.custom_storage.MediaStorage"
else:
    DEFAULT_FILE_STORAGE = "api.custom_storage.MediaStorageDev"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "api.authentication.CustomAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": False,
}

if ENVIRONMENT == "TEST":
    BASE_URL = "https://app.trydownstream.com"
    STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY")
    STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")
    STRIPE_FULL_CUSTOMER_PORTAL_CONFIG = env("STRIPE_FULL_CUSTOMER_PORTAL_CONFIG")
    STRIPE_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG = env("STRIPE_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG")
    AUTH0_CLIENT_ID = env("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET = env("AUTH0_CLIENT_SECRET")
    AUTH0_DOMAIN = "dev-jy1f5kgzroj4fcci.us.auth0.com"
    CHECKBOOK_ENDPOINT = "https://api.checkbook.io/v3/"
    CHECKBOOK_CLIENT_ID = env("CHECKBOOK_CLIENT_ID")
    CHECKBOOK_API_KEY = env("CHECKBOOK_API_KEY")
    CHECKBOOK_API_SECRET = env("CHECKBOOK_API_SECRET")
    CHECKBOOK_WEBHOOK_KEY = env("CHECKBOOK_WEBHOOK_KEY")
    BASIS_THEORY_USE_PCI_API_KEY = "key_prod_us_pvt_Ao9oRbvvTyT4d1Ew2M6Uxi"  # env("BASIS_THEORY_USE_PCI_API_KEY")
    BASIS_THEORY_READ_PCI_API_KEY = env("BASIS_THEORY_READ_PCI_API_KEY")
    BASIS_THEORY_MANGEMENT_API_KEY = env("BASIS_THEORY_MANGEMENT_API_KEY")
    BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID = env("BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID")
    BASIS_THEORY_APPLICATION_ID = "63da13bb-3a2c-4bd5-b747-a5a4cc9f76e7"  # env("BASIS_THEORY_APPLICATION_ID")
    BETTERSTACK_TOKEN = env("BETTERSTACK_DJANGO_PROD_TOKEN")
    # https://docs.lob.com/#tag/Authentication/API-Keys
    LOB_API_HOST = "https://api.lob.com/v1"
    LOB_API_KEY = env("LOB_API_KEY")
    LOB_PUB_API_KEY = env("LOB_DEV_PUB_API_KEY")
    LOB_CHECK_TEMPLATE_ID = "tmpl_e67263addbfe12c"
else:
    BASE_URL = "https://downstream-customer-dev.web.app"
    STRIPE_PUBLISHABLE_KEY = env("STRIPE_DEV_PUBLISHABLE_KEY")
    STRIPE_SECRET_KEY = env("STRIPE_DEV_SECRET_KEY")
    STRIPE_FULL_CUSTOMER_PORTAL_CONFIG = env("STRIPE_DEV_FULL_CUSTOMER_PORTAL_CONFIG")
    STRIPE_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG = env("STRIPE_DEV_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG")
    AUTH0_DOMAIN = "dev-8q3q3q3q.us.auth0.com"
    AUTH0_DOMAIN = "downstream-dev.us.auth0.com"
    AUTH0_CLIENT_ID = env("AUTH0_DEV_CLIENT_ID")
    AUTH0_CLIENT_SECRET = env("AUTH0_DEV_CLIENT_SECRET")
    CHECKBOOK_ENDPOINT = "https://api.sandbox.checkbook.io/v3/"
    CHECKBOOK_CLIENT_ID = env("CHECKBOOK_DEV_CLIENT_ID")
    CHECKBOOK_API_KEY = env("CHECKBOOK_DEV_API_KEY")
    CHECKBOOK_API_SECRET = env("CHECKBOOK_DEV_API_SECRET")
    CHECKBOOK_WEBHOOK_KEY = env("CHECKBOOK_DEV_WEBHOOK_KEY")
    BASIS_THEORY_USE_PCI_API_KEY = env("BASIS_DEV_THEORY_USE_PCI_API_KEY")
    BASIS_THEORY_READ_PCI_API_KEY = env("BASIS_DEV_THEORY_READ_PCI_API_KEY")
    BASIS_THEORY_MANGEMENT_API_KEY = env("BASIS_DEV_THEORY_MANGEMENT_API_KEY")
    BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID = env("BASIS_DEV_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID")
    BASIS_THEORY_APPLICATION_ID = "a44b44d5-2cb8-4255-bbf6-dc5884bffdbf"  # env("BASIS_DEV_THEORY_APPLICATION_ID")
    BETTERSTACK_TOKEN = env("BETTERSTACK_DJANGO_DEV_TOKEN")
    LOB_API_HOST = "https://api.lob.com/v1"
    LOB_API_KEY = env("LOB_DEV_API_KEY")
    LOB_PUB_API_KEY = env("LOB_DEV_PUB_API_KEY")
    LOB_CHECK_TEMPLATE_ID = "tmpl_72955c3cec0e752"

# Django Admin Interface settings.
X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

# OIDC settings
OIDC_RP_CLIENT_ID = env("OIDC_RP_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = env("OIDC_RP_CLIENT_SECRET")
OIDC_OP_AUTHORIZATION_ENDPOINT = env("OIDC_OP_AUTHORIZATION_ENDPOINT")
OIDC_OP_TOKEN_ENDPOINT = env("OIDC_OP_TOKEN_ENDPOINT")
OIDC_OP_USER_ENDPOINT = env("OIDC_OP_USER_ENDPOINT")
OIDC_RP_SIGN_ALGO = env("OIDC_RP_SIGN_ALGO")
OIDC_OP_JWKS_ENDPOINT = env("OIDC_OP_JWKS_ENDPOINT")
OIDC_OP_LOGOUT_ENDPOINT = env("OIDC_OP_LOGOUT_ENDPOINT")
OIDC_OP_LOGOUT_METHOD = env("OIDC_OP_LOGOUT_METHOD")
ALLOW_LOGOUT_GET_METHOD = True
# We don't want automatic user creation
OIDC_CREATE_USER = False

# Intercom Access Token.
INTERCOM_ACCESS_TOKEN = env("INTERCOM_ACCESS_TOKEN")

# MailChimp Access Token
MAILCHIMP_API_KEY = env("MAILCHIMP_API_KEY")


# Python Logging
# Django help: https://docs.djangoproject.com/en/5.0/topics/logging/
# BetterStack help: https://betterstack.com/docs/logs/python/
# Differentiate uncaught exceptions: https://betterstack.com/community/questions/how-to-log-uncaught-exceptions-in-python/
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "logtail": {
            "class": 'logtail.LogtailHandler',
            "source_token": BETTERSTACK_TOKEN,
        },
    },
    "loggers": {
        "stripe": {
            "handlers": [
                "logtail",
            ],
            # Set to WARNING to limit logs from Stripe Cron job (cost savings: large data throughput)
            "level": "WARNING",
        },
        "apscheduler.executors.default": {
            "handlers": [
                "logtail",
            ],
            # Set to WARNING to limit logs from Stripe Cron job (cost savings: large data throughput)
            "level": "WARNING",
        },
        "billing": {
            "handlers": [
                "logtail",
            ],
            "level": "INFO",
        },
        "": {
            "handlers": [
                "logtail",
            ],
            "level": "INFO",
        },
    },
}
