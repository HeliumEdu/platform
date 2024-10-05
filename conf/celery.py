"""
Initialize Celery with Django configuration.
"""

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.0"

import os

from celery import Celery
from celery.signals import task_failure
from django.conf import settings

from conf.configcache import config

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

app = Celery('conf')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

if not settings.DEBUG and os.environ.get('PLATFORM_WORKER_MODE', 'False') == 'True' and hasattr(settings, 'ROLLBAR'):
    import rollbar

    rollbar.init(**settings.ROLLBAR)


    def celery_base_data_hook(request, data):
        data['framework'] = 'celery'


    rollbar.BASE_DATA_HOOK = celery_base_data_hook


    @task_failure.connect
    def handle_task_failure(**kwargs):
        rollbar.report_exc_info(extra_data=kwargs)
