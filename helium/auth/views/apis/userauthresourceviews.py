__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import ViewSet, GenericViewSet

from helium.auth.models import UserSettings
from helium.auth.serializers.tokenserializer import TokenResponseFieldsMixin
from helium.auth.serializers.userserializer import UserSerializer, UserCreateSerializer, UserForgotSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.services import authservice
from helium.common.utils import taskutils
from helium.common.views.base import HeliumAPIView
from helium.importexport.tasks import import_example_schedule

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.register']
)
class UserRegisterResourceView(GenericViewSet, HeliumAPIView, CreateModelMixin):
    serializer_class = UserSerializer

    @extend_schema(
        operation_id='register',
        request=UserCreateSerializer,
        responses={
            201: UserSerializer

        }
    )
    def register(self, request, *args, **kwargs):
        """
        Register a new user.
        """
        response = self.create(request, *args, **kwargs)

        if 'time_zone' in request.data:
            user_settings = UserSettings.objects.get(user_id=response.data['id'])
            serializer = UserSettingsSerializer(user_settings, data={'time_zone': request.data['time_zone']}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            response.data['settings'] = serializer.data

        # Import the example schedule for the user (after timezone is set)
        taskutils.safe_apply_async(import_example_schedule,
            args=(response.data['id'],),
            kwargs={'example_schedule': request.data.get('example_schedule', True)},
            critical=True,
            priority=settings.CELERY_PRIORITY_HIGH,
        )

        logger.info(f"User {response.data['id']} created")

        return response


@extend_schema(
    tags=['auth.register']
)
class UserVerifyResourceView(ViewSet, HeliumAPIView):
    serializer_class = TokenResponseFieldsMixin

    @extend_schema(
        operation_id='verify_email',
        parameters=[
            OpenApiParameter('username', description="The user's email address."),
            OpenApiParameter('code', description=get_user_model()._meta.get_field('verification_code').help_text)
        ],
        responses={
            202: TokenResponseFieldsMixin
        }
    )
    def verify_email(self, request, *args, **kwargs):
        """
        Verify an email address for the user instance associated with the email and verification code.

        Returns access and refresh tokens for immediate authentication.
        """
        response = authservice.verify_email(request)

        return response


@extend_schema(
    tags=['auth.register']
)
class UserResendVerificationResourceView(ViewSet, HeliumAPIView):
    serializer_class = UserSerializer

    @extend_schema(
        operation_id='resend_verification_email',
        parameters=[
            OpenApiParameter('username', description="The user's email address.")
        ],
        responses={
            202: OpenApiResponse(description='Verification email queued. Returned whether or not the submitted '
                                              'address is registered, so callers cannot use this endpoint to '
                                              'probe account existence.'),
            429: OpenApiResponse(description='Throttled. Only one resend per submitted email is allowed per '
                                              '60 seconds; retry after the window.'),
        }
    )
    def resend_verification(self, request, *args, **kwargs):
        """
        Resend the verification email for an inactive user account, or for an active user who has requested an
        email change.
        """
        response = authservice.resend_verification_email(request)

        return response


class UserForgotResourceView(ViewSet, HeliumAPIView):
    serializer_class = UserSerializer

    @extend_schema(
        operation_id='forgot_password',
        request=UserForgotSerializer,
        responses={202: None}
    )
    def forgot_password(self, request, *args, **kwargs):
        """
        Reset the password for the user instance associated with the given email. Always responds
        with 202 (no body) regardless of whether the email is registered.
        """
        response = authservice.forgot_password(request)

        return response
