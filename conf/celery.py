"""
Initialize Celery with Django configuration.
"""

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.8"

import os
import sys

from celery.signals import task_failure
from django.conf import settings

from celery import Celery

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

app = Celery('conf')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

if 'celery' in sys.argv[0] and hasattr(settings, 'ROLLBAR'):
    import rollbar

    rollbar.init(**settings.ROLLBAR)


    def celery_base_data_hook(request, data):
        data['framework'] = 'celery'


    rollbar.BASE_DATA_HOOK = celery_base_data_hook


    @task_failure.connect
    def handle_task_failure(**kwargs):
        rollbar.report_exc_info(extra_data=kwargs)
