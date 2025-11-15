__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.7"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.auth.filters import UserPushTokenFilter
from helium.auth.models.userpushtoken import UserPushToken
from helium.auth.serializers.userpushtokenserializer import UserPushTokenSerializer
from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.pushtoken']
)
class UserPushTokenApiListView(HeliumAPIView, CreateModelMixin, ListModelMixin):
    serializer_class = UserPushTokenSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = UserPushTokenFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.push_tokens.all()
        else:
            return UserPushToken.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all push token instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        responses={
            201: UserPushTokenSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new push token instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"Push Token {response.data['id']} created for user {request.user.get_username()}")

        return response


@extend_schema(
    tags=['auth.pushtoken']
)
class UserPushTokenApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = UserPushTokenSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.push_tokens.all()
        else:
            return UserPushToken.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given push token instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given push token instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Push Token {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
