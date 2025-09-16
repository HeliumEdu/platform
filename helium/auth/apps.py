__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.33"

from django.apps import AppConfig
from django.db import models


class AuthConfig(AppConfig):
    name = 'helium.auth'
    label = 'helium_auth'
    verbose_name = 'Authentication'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import helium.auth.handlers
