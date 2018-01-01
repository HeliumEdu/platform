import logging

import coreapi
import coreschema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Material
from helium.planner.views.apis.schemas.materialgroupschemas import SubMaterialGroupListSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class MaterialListSchema(SubMaterialGroupListSchema):
    """
    If Django Rest Framework adds better support for properly getting the `help_text` of related fields,
    this can be removed
    """
    def get_link(self, path, method, base_url):
        link = super(MaterialListSchema, self).get_link(path, method, base_url)

        if method == 'POST':
            fields = list(link.fields)

            for i, field in enumerate(fields):
                if field.name == 'courses':
                    fields.pop()

                    break

            fields.append(
                coreapi.Field(
                    "courses",
                    required=False,
                    location="form",
                    schema=coreschema.Array(items=coreschema.Integer,
                                            title='courses',
                                            description=Material._meta.get_field('courses').help_text)
                )
            )

            return coreapi.Link(
                url=link.url,
                action=link.action,
                encoding=link.encoding,
                fields=fields,
                description=link.description
            )

        return link


class MaterialIDSchema(BaseIDSchema, MaterialListSchema):
    def __init__(self):
        super(MaterialIDSchema, self).__init__('material')
