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
from django.core.management.utils import get_random_secret_key

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-0+dmu6*lky0l743o^27tn0)dzoi)6-lzb1i)egsso_84h"
)


ENVIRONMENT = os.getenv("ENV")
DEBUG = os.getenv("ENV") == "TEST"
DEBUG = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    # START:  Django Admin Interface
    "admin_interface",
    "colorfield",
    # END:  Django Admin Interface
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    # START: Django Apps.
    "api",
    "notifications",
    # END: Django Apps.
    "api.pricing_ml",
    "api.utils",
    "django_filters",
    "drf_spectacular",
    "django_extensions",
    "django_apscheduler",
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


# Database.
if ENVIRONMENT == "TEST":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "defaultdb",
            "USER": "doadmin",
            "PASSWORD": "AVNS_XEihnXpBlng33jia5Xq",
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
            "PASSWORD": "AVNS_BAJyvGbMyyQNzKfrP0S",
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

# Amazon Web Services S3 Configuration.
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_ACCESS_KEY_ID = "AKIAYR4ELQCIAKOINOXF"
AWS_SECRET_ACCESS_KEY = "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"
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
    BASE_URL = "https://app.trydownstream.io"
    STRIPE_PUBLISHABLE_KEY = "pk_live_H293e3qNvoJB8isKoALzyCFs00v6DmDPGg"
    STRIPE_SECRET_KEY = "sk_live_wYw9ZQ4Gzp8V1n2EOVJ7ZRFW00DX5CyS6c"
    STRIPE_FULL_CUSTOMER_PORTAL_CONFIG = "bpc_1HJm0bGVYGkmHIWnUWCqt7sf"
    STRIPE_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG = "bpc_1Nvm05GVYGkmHIWnZLJPQrcc"
    AUTH0_CLIENT_ID = "zk3ULUpybm5gp0FyBcKE0k8WUPVdaDW3"
    AUTH0_CLIENT_SECRET = (
        "srBzQ02G9r4IVQ9F1S2P1yW_hYsS-ly-XI_DbMOeoqVGvdRea-hocCdYYOdaiFZv"
    )
    AUTH0_DOMAIN = "dev-jy1f5kgzroj4fcci.us.auth0.com"
    CHECKBOOK_ENDPOINT = "https://api.checkbook.io/v3/"
    CHECKBOOK_CLIENT_ID = "09650b96495b4447b97f4ab89c58df37"
    CHECKBOOK_API_KEY = "deb0f9a94051421fb128c9c6cea47c6d"
    CHECKBOOK_API_SECRET = "LafhEmkgGIdiAZB5Tryz3XNh2rU7KK"
    CHECKBOOK_WEBHOOK_KEY = "65840ee7b90442559953a6d925bc53a5"
else:
    BASE_URL = "https://downstream-customer-dev.web.app"
    STRIPE_PUBLISHABLE_KEY = "pk_test_xC1Nf1Djo2wx3DF72PmBiC5W00bBLUgjpf"
    STRIPE_SECRET_KEY = "sk_test_k7kzz0R6mrRogFPs6OVrpgrB00UmEjcUtf"
    STRIPE_FULL_CUSTOMER_PORTAL_CONFIG = "bpc_1MqjpaGVYGkmHIWnGRmlbTOk"
    STRIPE_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG = "bpc_1Nvkw9GVYGkmHIWnhHzyEsjn"
    AUTH0_DOMAIN = "dev-8q3q3q3q.us.auth0.com"
    AUTH0_CLIENT_ID = "KduQpQUG12d7jS8wP6d6cof6o64BFHx2"
    AUTH0_CLIENT_SECRET = (
        "XGRLBdAQ0lV9Xm4Bh_nmT3Yxc8ohF1f_7XtDmKwxn4uR_RCXMGIFEpDHS2bYazKb"
    )
    AUTH0_DOMAIN = "downstream-dev.us.auth0.com"
    CHECKBOOK_ENDPOINT = "https://api.sandbox.checkbook.io/v3/"
    CHECKBOOK_CLIENT_ID = "e689af74d3164255a5c6b9711eb4a71e"
    CHECKBOOK_API_KEY = "05658b72728c44c39b84ec174d70273a"
    CHECKBOOK_API_SECRET = "guqPM73fjlPNHddM8GjyVTdKWQIGXE"
    CHECKBOOK_WEBHOOK_KEY = "660813c1ab214bfa8458b81b983cf767"

# Django Admin Interface settings.
X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]
