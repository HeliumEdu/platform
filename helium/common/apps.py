from django.apps import AppConfig
from health_check.plugins import plugin_dir

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class CommonConfig(AppConfig):
    name = 'helium.common'
    verbose_name = 'Common'

    def ready(self):
        from health_check.contrib.s3boto_storage.backends import S3BotoStorageBackend
        plugin_dir.reregister(S3BotoStorageBackend.__name__,
                              type('S3StorageBackend', (S3BotoStorageBackend,), {'critical': False}))

        from health_check.contrib.twilio.backends import TwilioBackend
        plugin_dir.reregister(TwilioBackend.__name__,
                              type(TwilioBackend.__name__, (TwilioBackend,), {'critical': False, 'services': ['SMS']}))
