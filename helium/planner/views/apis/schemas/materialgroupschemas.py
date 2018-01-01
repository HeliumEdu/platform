import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Material

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class SubMaterialGroupListSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "material_group",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Material._meta.get_field('material_group').help_text)
            ),
        ]

        super(SubMaterialGroupListSchema, self).__init__(manual_fields=manual_fields)


class MaterialGroupIDSchema(BaseIDSchema):
    def __init__(self):
        super(MaterialGroupIDSchema, self).__init__('material group')
