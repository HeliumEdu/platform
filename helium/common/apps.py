import sys
from celery import current_app
from django.apps import AppConfig
from django.conf import settings
from health_check.plugins import plugin_dir
from urllib.parse import urlparse

__author__ = "Alex Laird"
__copyright__ = "Copyright 2021, Helium Edu"
__version__ = "1.4.46"


class CommonConfig(AppConfig):
    name = 'helium.common'
    verbose_name = 'Common'

    def ready(self):
        self.init_ngrok()

        plugin_dir.reset()

        from health_check.db.backends import DatabaseBackend
        from health_check.cache.backends import CacheBackend
        from health_check.contrib.celery.backends import CeleryHealthCheck
        from health_check.contrib.s3boto3_storage.backends import S3Boto3StorageHealthCheck
        from health_check.contrib.twilio.backends import TwilioHealthCheck

        plugin_dir.register(type('Database', (DatabaseBackend,),
                                 {
                                     'description': 'The database is critical for a fully operational system'
                                 }))
        plugin_dir.register(type('Cache', (CacheBackend,),
                                 {
                                     'description': 'The caching service is critical for a fully operational system'
                                 }))
        plugin_dir.register(type('TaskProcessing', (CeleryHealthCheck,),
                                 {
                                     'description': 'Grade calculation, emails, text messages, and other '
                                                    'deferred tasks',
                                     'queues': current_app.amqp.queues
                                 }))

        plugin_dir.register(type('Twilio', (TwilioHealthCheck,),
                                 {
                                     'critical': False,
                                     'description': 'Reminders and other text message notifications',
                                     'services': ['SMS']
                                 }))

        if not settings.SERVE_LOCAL:
            plugin_dir.register(type('AWS', (S3Boto3StorageHealthCheck,),
                                     {
                                         'critical': False,
                                         'description': 'Attachment and other file storage'
                                     }))

    def init_ngrok(self):
        if settings.DEV_SERVER and settings.USE_NGROK:
            # pyngrok will only be installed, and should only ever be initialized, in a dev environment
            from pyngrok import ngrok

            # Get the dev server port (defaults to 8000 for Django, can be overridden with the
            # last arg when calling `runserver`)
            addrport = urlparse(f"http://{sys.argv[-1]}")
            port = addrport.port if addrport.netloc and addrport.port else 8000

            # Open a ngrok tunnel to the dev server
            public_url = ngrok.connect(port).public_url
            print(f"ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")

            # Update any base URLs or webhooks to use the public ngrok URL
            settings.PROJECT_HOST = public_url
