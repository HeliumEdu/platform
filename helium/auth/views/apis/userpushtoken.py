import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.auth.filters import UserPushTokenFilter
from helium.auth.models.userpushtoken import UserPushToken
from helium.auth.serializers.userpushtokenserializer import UserPushTokenSerializer
from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
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

    def _reclaim_device_from_other_accounts(self, token) -> None:
        """
        Retire any other account's registration for this device.

        FCM issues one token per install, so the same token under a different user means the device
        changed hands. A client whose session expired rather than being signed out cannot reach the
        API to retire its own registration, so the account signing in does it.

        :param token: the registration token being claimed.
        """
        reclaimed, _ = UserPushToken.objects.filter(token=token).exclude(user=self.request.user).delete()

        if reclaimed:
            logger.info(f'Reclaimed {reclaimed} push token(s) from a previous account on this device')
            metricutils.increment('action.push.token.reclaimed', value=reclaimed)

    def perform_create(self, serializer):
        token = serializer.validated_data['token']

        self._reclaim_device_from_other_accounts(token)

        obj, _ = UserPushToken.objects.update_or_create(
            user=self.request.user,
            device_id=serializer.validated_data['device_id'],
            defaults={'token': token},
        )
        serializer.instance = obj

    def post(self, request, *args, **kwargs):
        """
        Create or update the push token for the authenticated user's device.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"Push Token {response.data['id']} registered for user {request.user.pk}")

        return response


@extend_schema(exclude=True)
class UserPushTokenApiDetailView(HeliumAPIView, UpdateModelMixin, DestroyModelMixin):
    serializer_class = UserPushTokenSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.push_tokens.all()
        else:
            return UserPushToken.objects.none()

    def delete(self, request, *args, **kwargs):
        """
        Delete the given push token instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Push Token {kwargs['pk']} deleted for user {request.user.pk}")

        return response
