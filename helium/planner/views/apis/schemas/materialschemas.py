import logging

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.views.apis.schemas.materialgroupschemas import SubMaterialGroupListSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class MaterialDetailSchema(BaseIDSchema, SubMaterialGroupListSchema):
    def __init__(self):
        super(MaterialDetailSchema, self).__init__('material')
