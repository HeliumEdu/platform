__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os

import certifi
from django.conf import settings
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

application = get_wsgi_application()

# Only start the monitor if we're using a non-dev web server and not in production
if not settings.DEV_SERVER:
    from conf import monitor

    monitor.start()
