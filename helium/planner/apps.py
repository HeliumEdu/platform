__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.6.1"

from django.apps import AppConfig


class PlannerConfig(AppConfig):
    name = 'helium.planner'
    verbose_name = 'Planner'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import helium.planner.handlers
