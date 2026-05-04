__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.common.views.base import HeliumAPIView
from helium.planner.services import calendarservice

logger = logging.getLogger(__name__)


class UserSettingsApiDetailView(HeliumAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        """
        Update the authenticated user's settings. This endpoint only updates the fields given (i.e. no need to PATCH
        for partials data).
        """
        user = self.get_object()

        old_time_zone = user.settings.time_zone

        serializer = self.get_serializer(user.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        new_time_zone = serializer.data.get('time_zone')
        if new_time_zone and new_time_zone != old_time_zone:
            # Run synchronously so the next GET reflects the rebased dates — otherwise the
            # client (which may already be rendering the planner) would briefly show all-day
            # events spanning two days in the new timezone.
            calendarservice.normalize_all_day_for_timezone_change(user, old_time_zone, new_time_zone)

        logger.info(f'Settings updated for user {user.pk}')

        return Response(serializer.data)
