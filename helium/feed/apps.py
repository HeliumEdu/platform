__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

from django.apps import AppConfig


class FeedConfig(AppConfig):
    name = 'helium.feed'
    verbose_name = 'Feed'
    default_auto_field = 'django.db.models.AutoField'
