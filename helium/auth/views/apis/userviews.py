__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.tasks import delete_user
from helium.common.permissions import IsOwner
from helium.common.utils import metricutils, taskutils
from helium.common.throttles import DeleteInactiveUserThrottle
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


def _reserve_pending_delete(user):
    user.deletion_requested_at = timezone.now()
    user.save(update_fields=['deletion_requested_at'])

    for outstanding in OutstandingToken.objects.filter(user=user):
        try:
            RefreshToken(outstanding.token).blacklist()
        except TokenError:
            # Already expired or blacklisted — safe to ignore
            pass


class UserApiDetailView(HeliumAPIView, RetrieveModelMixin):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsOwner)

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary='Retrieve the authenticated User',
        tags=['auth']
    )
    def get(self, request, *args, **kwargs):
        """
        Return the authenticated user instance, including settings details.
        """
        user = self.get_object()

        serializer = self.get_serializer(user)

        return Response(serializer.data)

    @extend_schema(summary='Update the authenticated User')
    def put(self, request, *args, **kwargs):
        """
        Update the authenticated user instance. This endpoint only updates the fields given (i.e. no need to PATCH
        for partials data).
        """
        user = self.get_object()

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f'User {user.pk} updated')

        return Response(serializer.data)


class UserDeleteResourceView(HeliumAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    @extend_schema(summary='Delete the authenticated User account')
    def delete(self, request, *args, **kwargs):
        """
        Permanently delete the authenticated user's account and all associated data (courses,
        homework, events, attachments, reminders, notes, schedules, external calendars). This
        operation is irreversible.

        For users with a usable password, the request body must include the user's current
        password to confirm the action:

            {"password": "<current-password>"}

        OAuth-only users (no usable password) may submit an empty body; the access token already
        proves authentication.

        The response is immediate. Outstanding refresh tokens are blacklisted before returning, but the
        actual data deletion runs in the background — accounts and their data may persist for a short
        window after the response.
        """
        user = self.get_object()

        # Only require password verification if user has a usable password
        if user.has_usable_password():
            if 'password' not in request.data:
                raise ValidationError({'password': ['This field is required.']})

            if not user.check_password(request.data['password']):
                raise ValidationError({'password': ['The password is incorrect.']})

        logger.info(f'User {user.pk} will be deleted')

        _reserve_pending_delete(user)

        taskutils.safe_apply_async(delete_user, args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDeleteInactiveResourceView(HeliumAPIView):
    serializer_class = UserSerializer

    def get_throttles(self):
        from rest_framework.settings import api_settings
        if not api_settings.DEFAULT_THROTTLE_CLASSES:
            return []
        return [DeleteInactiveUserThrottle()]

    def get_object(self):
        UserModel = get_user_model()
        # `username` accepted as an undocumented back-compat alias for `email`.
        identifier = self.request.data.get('email') or self.request.data.get('username')
        try:
            return UserModel.objects.get(
                Q(email__iexact=identifier) | Q(username__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            raise NotFound('No User matches the given query.')

    # Excluded from API docs - this endpoint is only needed by integration tests for cleanup
    @extend_schema(exclude=True)
    def delete(self, request, *args, **kwargs):
        """
        Delete an inactive user instance. The request body should include the `email` and `password`, and this route
        can only be used to delete users that never finished setting up their account.
        """
        if 'email' not in request.data and 'username' not in request.data:
            raise ValidationError({'email': ['This field is required.']})

        if 'password' not in request.data:
            raise ValidationError({'password': ['This field is required.']})

        if 'username' in request.data and 'email' not in request.data:
            metricutils.increment('api.deprecated_param.username', request=request)

        user = self.get_object()

        if user.is_active:
            raise ValidationError({'non_field_errors': ['This endpoint can only be used to clean up user accounts that '
                                                  'were never activated.']})

        if not user.check_password(request.data['password']):
            raise AuthenticationFailed({'password': ['The password is incorrect.']})

        logger.info(f'User {user.pk} will be deleted')

        _reserve_pending_delete(user)

        taskutils.safe_apply_async(delete_user, args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)

        return Response(status=status.HTTP_204_NO_CONTENT)
