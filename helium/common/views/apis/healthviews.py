from django.views.decorators.cache import never_cache
from health_check.views import MainView
from rest_framework.viewsets import ViewSet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.9'


class HealthResourceView(MainView, ViewSet):
    """
    health:
    Return the results of a basic health check on the app.
    """

    @never_cache
    def health(self, request, *args, **kwargs):
        return super().get(request, args, kwargs)
