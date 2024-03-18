__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.6.0"

from django.apps import AppConfig


class FeedConfig(AppConfig):
    name = 'helium.feed'
    verbose_name = 'Feed'
    default_auto_field = 'django.db.models.BigAutoField'
