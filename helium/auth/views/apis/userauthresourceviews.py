__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import ViewSet, GenericViewSet

from helium.auth.serializers.tokenserializer import TokenResponseFieldsMixin
from helium.auth.serializers.userserializer import UserSerializer, UserCreateSerializer, UserForgotSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.services import authservice
from helium.common.views.base import HeliumAPIView
from helium.importexport.tasks import import_example_schedule

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.register']
)
class UserRegisterResourceView(GenericViewSet, HeliumAPIView, CreateModelMixin):
    serializer_class = UserSerializer

    @extend_schema(
        request=UserCreateSerializer,
        responses={
            201: UserSerializer

        }
    )
    def register(self, request, *args, **kwargs):
        """
        Register a new user.
        """
        UserModel = get_user_model()

        response = self.create(request, *args, **kwargs)

        if 'time_zone' in request.data:
            user_settings = UserModel.objects.get(pk=response.data['id']).settings
            serializer = UserSettingsSerializer(user_settings, data={'time_zone': request.data['time_zone']}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            response.data['settings'] = serializer.data

        # Import the example schedule for the user (after timezone is set)
        import_example_schedule.apply_async(
            args=(response.data['id'],),
            kwargs={'example_schedule': request.data.get('example_schedule', True)},
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
        parameters=[
            OpenApiParameter('username', description='The username for the user.'),
            OpenApiParameter('code', description=get_user_model()._meta.get_field('verification_code').help_text)
        ],
        responses={
            202: TokenResponseFieldsMixin
        }
    )
    def verify_email(self, request, *args, **kwargs):
        """
        Verify an email address for the user instance associated with the username and verification code.

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
        parameters=[
            OpenApiParameter('username', description='The username for the user.')
        ],
        responses={
            202: None,
            429: None
        }
    )
    def resend_verification(self, request, *args, **kwargs):
        """
        Resend the verification email for an inactive user account.
        Rate limited to once per 60 seconds per user.
        """
        response = authservice.resend_verification_email(request)

        return response


class UserForgotResourceView(ViewSet, HeliumAPIView):
    serializer_class = UserSerializer

    @extend_schema(
        request=UserForgotSerializer,
        responses={
            202: UserSerializer
        }
    )
    def forgot_password(self, request, *args, **kwargs):
        """
        Reset the password for the user instance associated with the given email.
        """
        response = authservice.forgot_password(request)

        return response
