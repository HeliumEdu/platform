import logging

from django.urls import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.feed.serializers.privatefeedserializer import PrivateFeedSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


class PrivateEnableResourceView(ViewSet):
    """
    enable:
    Enable the private feed URLs for the authenticated user. It is safe to make this request multiple times, and if
    private feeds are already enabled, the response will simply contain links to the feeds.
    """
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def enable(self, request, *args, **kwargs):
        user = self.request.user

        user.settings.enable_private_slug()

        serializer = PrivateFeedSerializer({
            'events_private_url': reverse('feed_private_events_ical', kwargs={'slug': user.settings.private_slug}),
            'homework_private_url': reverse('feed_private_homework_ical', kwargs={'slug': user.settings.private_slug}),
            'courseschedules_private_url': reverse('feed_private_courseschedules_ical',
                                                   kwargs={'slug': user.settings.private_slug})
        })

        return Response(serializer.data)


class PrivateDisableResourceView(ViewSet):
    """
    disable:
    Disable the private feed URLs for the authenticated user.
    """
    permission_classes = (IsAuthenticated,)

    def disable(self, request, *args, **kwargs):
        user = self.request.user

        user.settings.disable_private_slug()

        return Response()
