__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.apps import AppConfig


class AuthConfig(AppConfig):
    name = 'helium.auth'
    label = 'helium_auth'
    verbose_name = 'Authentication'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import helium.auth.handlers
