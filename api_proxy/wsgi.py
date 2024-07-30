"""
WSGI config for api_proxy project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

from django.core.wsgi import get_wsgi_application
import os
import newrelic.agent
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
newrelic.agent.initialize(BASE_DIR / 'newrelic.ini')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_proxy.settings')

application = get_wsgi_application()
