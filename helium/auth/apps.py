__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from django.apps import AppConfig


class AuthConfig(AppConfig):
    name = 'helium.auth'
    label = 'helium_auth'
    verbose_name = 'Authentication'
    default_auto_field = 'django.db.models.BigAutoField'
