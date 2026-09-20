import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.services import authservice
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


class UserSetupView(HeliumAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    @extend_schema(summary="Provision the authenticated User",
                   request=None,
                   responses={status.HTTP_200_OK: UserSettingsSerializer})
    def post(self, request, *args, **kwargs):
        """
        Provision the authenticated user's account with the example schedule.
        """
        user = self.get_object()

        authservice.start_setup(user)

        user.settings.refresh_from_db()

        return Response(self.get_serializer(user.settings).data)
