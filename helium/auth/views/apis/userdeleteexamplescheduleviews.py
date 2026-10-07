import logging

from drf_spectacular.utils import extend_schema
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

    @extend_schema(exclude=True)
    def delete(self, request, *args, **kwargs):
        """
        Delete the untouched example schedule for the user instance, keeping anything that changed. Returns 204 when
        everything was deleted, or 200 with a message when anything was kept.
        """
        user = self.get_object()

        partial = delete_example_schedule(user.pk)

        logger.info(f'User {user.pk} deleted the example schedule')

        if partial:
            return Response({'message': 'The example schedule was cleared, except for anything that changed.'},
                            status=status.HTTP_200_OK)

        return Response(status=status.HTTP_204_NO_CONTENT)
