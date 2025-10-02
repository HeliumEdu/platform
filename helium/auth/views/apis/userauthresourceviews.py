__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.38"

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import ViewSet, GenericViewSet

from helium.auth.serializers.userserializer import UserSerializer, UserCreateSerializer, UserForgotSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.services import authservice
from helium.common.views.views import HeliumAPIView

logger = logging.getLogger(__name__)


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
        response = self.create(request, *args, **kwargs)

        if 'time_zone' in request.data:
            settings = get_user_model().objects.get(pk=response.data['id']).settings
            serializer = UserSettingsSerializer(settings, data={'time_zone': request.data['time_zone']}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            response.data['settings'] = serializer.data

        logger.info(f"User {response.data['id']} created with username {response.data['username']}")

        return response


class UserVerifyResourceView(ViewSet, HeliumAPIView):
    serializer_class = UserSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter('username', description='The username for the user.'),
            OpenApiParameter('code', description=get_user_model()._meta.get_field('verification_code').help_text)
        ],
        responses={
            202: UserSerializer
        }
    )
    def verify_email(self, request, *args, **kwargs):
        """
        Verify an email address for the user instance associated with the username and verification code.
        """
        response = authservice.verify_email(request)

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
