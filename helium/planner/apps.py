__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.apps import AppConfig


class PlannerConfig(AppConfig):
    name = 'helium.planner'
    verbose_name = 'Planner'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import helium.planner.handlers
