__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.services.authservice import delete_example_schedule
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


class UserDeleteExampleScheduleView(HeliumAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def delete(self, request, *args, **kwargs):
        """
        Delete any items marked as part of the example schedule for the user instance.
        """
        user = self.get_object()

        delete_example_schedule(user.pk)

        logger.info(f'User {user.get_username()} deleted the example schedule')

        return Response(status=status.HTTP_204_NO_CONTENT)
