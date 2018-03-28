from django.apps import AppConfig

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.4'


class PlannerConfig(AppConfig):
    name = 'helium.planner'
    verbose_name = 'Planner'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import helium.planner.handlers
