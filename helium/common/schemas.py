import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

__author__ = "Alex Laird"
__copyright__ = "Copyright 2021, Helium Edu"
__version__ = "1.4.46"

logger = logging.getLogger(__name__)


class BaseIDSchema(AutoSchema):
    """
    If Django Rest Framework adds betters support for properly getting the `help_text` from models, this schema
    can be removed.
    """

    def __init__(self, model_name, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "id",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=f'A unique integer value identifying this {model_name}.')
            ),
        ]

        super().__init__(manual_fields=manual_fields)
