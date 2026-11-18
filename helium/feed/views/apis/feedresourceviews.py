import logging

from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from helium.common.views.base import HeliumAPIView
from helium.feed.serializers.feedserializer import FeedUrlsSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.private']
)
class FeedsEnableView(GenericViewSet, HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FeedUrlsSerializer

    @extend_schema(
        summary='Enable Feeds',
        request=None
    )
    def enable(self, request, *args, **kwargs):
        """
        Enable the Feed URLs for the authenticated user. It is safe to make this request multiple times, and if
        Feeds are already enabled, the response will simply contain links to the Feeds.
        """
        user = self.request.user

        user.settings.enable_private_slug()

        serializer = FeedUrlsSerializer({
            'events_private_url': reverse('feed_events', kwargs={'private_slug': user.settings.private_slug}),
            'homework_private_url': reverse('feed_homework', kwargs={'private_slug': user.settings.private_slug}),
            'courseschedules_private_url': reverse('feed_courseschedules',
                                                   kwargs={'private_slug': user.settings.private_slug}),
            'all_private_url': reverse('feed_all', kwargs={'private_slug': user.settings.private_slug}),
        })

        return Response(serializer.data)


@extend_schema(
    tags=['feed.private']
)
class FeedsDisableView(GenericViewSet, HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FeedUrlsSerializer

    @extend_schema(
        summary='Disable Feeds',
        request=None,
        responses={status.HTTP_204_NO_CONTENT: None}
    )
    def disable(self, request, *args, **kwargs):
        """
        Disable the Feed URLs for the authenticated user.
        """
        user = self.request.user

        user.settings.disable_private_slug()

        return Response(status=status.HTTP_204_NO_CONTENT)
