import logging

from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.feed.serializers.privatefeedserializer import PrivateFeedSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class PrivateEnableResourceView(APIView):
    """
    put:
    Enable the private feed URLs for the authenticated user.
    """
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def put(self, request, *args, **kwargs):
        user = self.request.user

        user.settings.enable_private_slug()

        serializer = PrivateFeedSerializer({
            'events_private_url': reverse('feed_private_events_ical', kwargs={'slug': user.settings.private_slug}),
            'homework_private_url': reverse('feed_private_homework_ical', kwargs={'slug': user.settings.private_slug})
        })

        return Response(serializer.data, status=status.HTTP_200_OK)


class PrivateDisableResourceView(APIView):
    """
    put:
    Disable the private feed URLs for the authenticated user.
    """
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        user = self.request.user

        user.settings.disable_private_slug()

        return Response(status=status.HTTP_200_OK)
