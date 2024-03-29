__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.common.views.views import HeliumAPIView

logger = logging.getLogger(__name__)


class UserSettingsApiDetailView(HeliumAPIView):
    """
    put:
    Update the authenticated user's settings. This endpoint only updates the fields given (i.e. no need to PATCH
    for partials data).

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    queryset = get_user_model().objects.all()
    serializer_class = UserSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = self.get_serializer(user.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f'Settings updated for user {user.get_username()}')

        return Response(serializer.data)
