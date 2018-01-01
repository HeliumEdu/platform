import logging

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.views.apis.schemas.courseschemas import SubCourseListSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CategoryIDSchema(BaseIDSchema, SubCourseListSchema):
    def __init__(self):
        super(CategoryIDSchema, self).__init__('category')
