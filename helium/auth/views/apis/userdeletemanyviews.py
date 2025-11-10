__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.62"

import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.tasks import delete_example_schedule
from helium.common.views.views import HeliumAPIView

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

        logger.info(f'User {user.get_username()} is deleting their example schedule')

        delete_example_schedule.delay(user.pk)

        return Response(status=status.HTTP_204_NO_CONTENT)
