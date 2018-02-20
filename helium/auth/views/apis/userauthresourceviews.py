import logging

from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import ViewSet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

logger = logging.getLogger(__name__)


class UserRegisterResourceView(GenericAPIView):
    """
    post:

    """

    def post(self, request, *args, **kwargs):
        raise NotImplementedError


class UserVerifyResourceView(ViewSet):
    """
    verify_email:

    """

    def verify_email(self, request, *args, **kwargs):
        raise NotImplementedError


class UserForgotResourceView(ViewSet):
    """
    forgot_password:

    """

    def forgot_password(self, request, *args, **kwargs):
        raise NotImplementedError
