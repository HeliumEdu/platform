from celery import current_app
from django.apps import AppConfig
from django.conf import settings

from health_check.plugins import plugin_dir

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.9'


class CommonConfig(AppConfig):
    name = 'helium.common'
    verbose_name = 'Common'

    def ready(self):
        from health_check.db.backends import DatabaseBackend
        from health_check.cache.backends import CacheBackend
        from health_check.contrib.celery.backends import CeleryHealthCheck
        from health_check.contrib.s3boto_storage.backends import S3BotoStorageHealthCheck
        from health_check.contrib.twilio.backends import TwilioHealthCheck

        plugin_dir.register(type('Database', (DatabaseBackend,),
                                 {
                                     'description': 'The database is critical for a fully operational system'
                                 }))
        plugin_dir.register(type('Cache', (CacheBackend,),
                                 {
                                     'description': 'The caching service is critical for a fully operational system'
                                 }))
        plugin_dir.register(type('Task Processing', (CeleryHealthCheck,),
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
            plugin_dir.register(type('AWS', (S3BotoStorageHealthCheck,),
                                     {
                                         'critical': False,
                                         'description': 'Attachment and other file storage'
                                     }))
