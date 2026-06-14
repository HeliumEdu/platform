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
from helium.auth.serializers.userserializer import UserSerializer, UserCreateSerializer, UserForgotSerializer, \
    UserForgotConfirmSerializer
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
        summary='Register a new User',
        request=UserCreateSerializer,
        responses={
            201: UserSerializer

        },
        auth=[],
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
        summary='Verify a User email',
        parameters=[
            OpenApiParameter('email', description="The user's email address.", required=True),
            OpenApiParameter('code', description=get_user_model()._meta.get_field('verification_code').help_text, required=True)
        ],
        responses={
            202: TokenResponseFieldsMixin
        },
        auth=[],
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
        summary='Resend the verification email',
        parameters=[
            OpenApiParameter('email', description="The user's email address.")
        ],
        responses={
            202: OpenApiResponse(description='Verification email queued. Returned whether or not the submitted '
                                              'address is registered, so callers cannot use this endpoint to '
                                              'probe account existence.'),
            429: OpenApiResponse(description='Throttled. Only one resend per submitted email is allowed per '
                                              '60 seconds.'),
        },
        auth=[],
    )
    def resend_verification(self, request, *args, **kwargs):
        """
        Resend the verification email for an inactive user account, or for an active user who has requested an
        email change.
        """
        response = authservice.resend_verification_email(request)

        return response


@extend_schema(tags=['auth.password-reset'])
class UserForgotResourceView(ViewSet, HeliumAPIView):
    serializer_class = UserSerializer

    @extend_schema(
        operation_id='forgot_password',
        summary='Request a password reset',
        request=UserForgotSerializer,
        responses={
            202: OpenApiResponse(description='Reset email queued. Returned whether or not the submitted '
                                             'address is registered, so callers cannot use this endpoint to '
                                             'probe account existence.'),
            429: OpenApiResponse(description='Throttled. Only one reset request per submitted email is '
                                             'allowed per 60 seconds.'),
        },
        auth=[],
    )
    def forgot_password(self, request, *args, **kwargs):
        """
        Send a password reset link to the given email address.
        """
        response = authservice.forgot_password(request)

        return response


@extend_schema(tags=['auth.password-reset'])
class UserForgotConfirmResourceView(ViewSet, HeliumAPIView):
    serializer_class = UserForgotConfirmSerializer

    @extend_schema(
        operation_id='confirm_password_reset',
        summary='Confirm a password reset',
        request=UserForgotConfirmSerializer,
        responses={200: None},
        auth=[],
    )
    def confirm_password_reset(self, request, *args, **kwargs):
        """
        Confirm a password reset using the ``uid`` and ``token`` from the reset email link, setting a new password.
        """
        response = authservice.confirm_password_reset(request)

        return response
