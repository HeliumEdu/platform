import logging

from django.contrib.auth import get_user_model
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import ViewSet, GenericViewSet

from helium.auth.schemas import UserRegisterSchema, UserVerifySchema, UserForgotSchema
from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.services import authservice
from helium.common.views.views import HeliumAPIView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


class UserRegisterResourceView(GenericViewSet, HeliumAPIView, CreateModelMixin):
    """
    register:
    Register a new user.
    """
    serializer_class = UserSerializer
    schema = UserRegisterSchema()

    def register(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        if 'time_zone' in request.data:
            settings = get_user_model().objects.get(pk=response.data['id']).settings
            serializer = UserSettingsSerializer(settings, data={'time_zone': request.data['time_zone']}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            response.data['settings'] = serializer.data

        logger.info('User {} created with username '.format(response.data['id'], response.data['username']))

        return response


class UserVerifyResourceView(ViewSet, HeliumAPIView):
    """
    verify_email:
    Verify an email address for the user instance associated with the username and verification code.
    """
    serializer_class = UserSerializer
    schema = UserVerifySchema()

    def verify_email(self, request, *args, **kwargs):
        response = authservice.verify_email(request)

        return response


class UserForgotResourceView(ViewSet, HeliumAPIView):
    """
    forgot_password:
    Reset the password for the user instance associated with the given email.
    """
    serializer_class = UserSerializer
    schema = UserForgotSchema()

    def forgot_password(self, request, *args, **kwargs):
        response = authservice.forgot_password(request)

        return response
