__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.19"

import logging

from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from helium.common.views.base import HeliumAPIView
from helium.feed.serializers.privatefeedserializer import PrivateFeedSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.private']
)
class PrivateEnableResourceView(GenericViewSet, HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PrivateFeedSerializer

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def enable(self, request, *args, **kwargs):
        """
        Enable the private feed URLs for the authenticated user. It is safe to make this request multiple times, and if
        private feeds are already enabled, the response will simply contain links to the feeds.
        """
        user = self.request.user

        user.settings.enable_private_slug()

        serializer = PrivateFeedSerializer({
            'events_private_url': reverse('feed_private_events_ical', kwargs={'private_slug': user.settings.private_slug}),
            'homework_private_url': reverse('feed_private_homework_ical', kwargs={'private_slug': user.settings.private_slug}),
            'courseschedules_private_url': reverse('feed_private_courseschedules_ical',
                                                   kwargs={'private_slug': user.settings.private_slug})
        })

        return Response(serializer.data)


@extend_schema(
    tags=['feed.private']
)
class PrivateDisableResourceView(GenericViewSet, HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PrivateFeedSerializer

    @extend_schema(
        responses={status.HTTP_204_NO_CONTENT: None}
    )
    def disable(self, request, *args, **kwargs):
        """
        Disable the private feed URLs for the authenticated user.
        """
        user = self.request.user

        user.settings.disable_private_slug()

        return Response(status=status.HTTP_204_NO_CONTENT)
