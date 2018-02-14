import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.5'

logger = logging.getLogger(__name__)


class TokenSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field("username", required=True, location="form",
                          schema=coreschema.String(title='username',
                                                   description="The username or email for the user.")),
            coreapi.Field("password", required=True, location="form",
                          schema=coreschema.String(title='password', description="The password for the user.")),
        ]

        super(TokenSchema, self).__init__(manual_fields=manual_fields)
