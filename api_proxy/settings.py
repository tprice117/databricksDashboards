"""
Django settings for api_proxy project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

from django.core.management.utils import get_random_secret_key
from pathlib import Path
import os
import sys
import dj_database_url

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", 'django-insecure-0+dmu6*lky0l743o^27tn0)dzoi)6-lzb1i)egsso_84h')


ENVIRONMENT = os.getenv('ENV')
DEBUG = os.getenv('DEBUG', "False") == "True"
DEBUG = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'api',
    # 'api.pricing_ml',
    'django_filters',
    'drf_spectacular',
    ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'api_proxy.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            str(BASE_DIR) + '/templates/',
        ],
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

WSGI_APPLICATION = 'api_proxy.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'defaultdb',
        'USER': 'doadmin',
        'PASSWORD': 'AVNS_XEihnXpBlng33jia5Xq',
        'HOST': 'db-postgresql-nyc1-05939-do-user-13480306-0.b.db.ondigitalocean.com',
        'PORT': '25060',
    }
}

# Database.
if ENVIRONMENT == 'TEST': #This is currently the server/db that is being used for App created by Tate
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'defaultdb',
            'USER': 'doadmin',
            'PASSWORD': 'AVNS_XEihnXpBlng33jia5Xq',
            'HOST': 'db-postgresql-nyc1-05939-do-user-13480306-0.b.db.ondigitalocean.com',
            'PORT': '25060',
        }
    }
elif ENVIRONMENT == 'DEV':
    #new db for development purposes 
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'defaultdb',
            'USER': 'doadmin',
            'PASSWORD': 'AVNS_BAJyvGbMyyQNzKfrP0S',
            'HOST': 'db-postgresql-nyc1-22939-do-user-13480306-0.b.db.ondigitalocean.com',
            'PORT': '25060',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'sqllite.db',
        },
    }

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Add these new lines
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# Add machine learning models
ML_MODELS = os.path.join(BASE_DIR, 'api/pricing_ml')

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

# DEFAULT_AUTO_FIELD = 'django.db.models.TextField'

CORS_ORIGIN_ALLOW_ALL = True
# CORS_ORIGIN_WHITELIST = [
#      'http://localhost:3000',
#      'http://localhost:62964',
# ]

CORS_ORIGIN_ALLOW_ALL = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.SessionAuthentication',
        # 'firebase_auth.firebase_authentication.FirebaseAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

if ENVIRONMENT == 'TEST':
    STRIPE_PUBLISHABLE_KEY = 'pk_live_H293e3qNvoJB8isKoALzyCFs00v6DmDPGg'
    STRIPE_SECRET_KEY = 'sk_live_wYw9ZQ4Gzp8V1n2EOVJ7ZRFW00DX5CyS6c'
else:    
    STRIPE_PUBLISHABLE_KEY = 'pk_test_xC1Nf1Djo2wx3DF72PmBiC5W00bBLUgjpf'
    STRIPE_SECRET_KEY = 'sk_test_k7kzz0R6mrRogFPs6OVrpgrB00UmEjcUtf' 

