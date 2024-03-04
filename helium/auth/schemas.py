__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import coreapi
import coreschema
from django.contrib.auth import get_user_model
from rest_framework.schemas import AutoSchema

from helium.auth.models import UserSettings
from helium.auth.serializers.userserializer import UserSerializer


class UserRegisterSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "username",
                required=True,
                location="form",
                schema=coreschema.String(title='username',
                                         description='A unique name used to login to the system.')
            ),
            coreapi.Field(
                "email",
                required=True,
                location="form",
                schema=coreschema.String(title='email',
                                         description=get_user_model()._meta.get_field('email').help_text)
            ),
            coreapi.Field(
                "password",
                required=True,
                location="form",
                schema=coreschema.String(title='password',
                                         description=UserSerializer._declared_fields.get('password').help_text)
            ),
            coreapi.Field(
                "time_zone",
                required=False,
                location="form",
                schema=coreschema.String(title='time_zone',
                                         description=UserSettings._meta.get_field('time_zone').help_text)
            ),
        ]

        super().__init__(manual_fields=manual_fields)


class UserVerifySchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "username",
                required=True,
                location="query",
                schema=coreschema.String(title='username',
                                         description='The username for the user.')
            ),
            coreapi.Field(
                "code",
                required=True,
                location="query",
                schema=coreschema.String(title='code',
                                         description='The email verification code for the user')
            ),
        ]

        super().__init__(manual_fields=manual_fields)


class UserDeleteSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "username",
                required=True,
                location="form",
                schema=coreschema.String(title='username',
                                         description='The username for the user.')
            ),
            coreapi.Field(
                "email",
                required=True,
                location="form",
                schema=coreschema.String(title='email',
                                         description='The email for the user.')
            ),
            coreapi.Field(
                "password",
                required=True,
                location="form",
                schema=coreschema.String(title='password',
                                         description='The password for the user.')
            ),
        ]

        super().__init__(manual_fields=manual_fields)


class UserForgotSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "email",
                required=True,
                location="form",
                schema=coreschema.String(title='email',
                                         description='The email for the user.')
            ),
        ]

        super().__init__(manual_fields=manual_fields)
