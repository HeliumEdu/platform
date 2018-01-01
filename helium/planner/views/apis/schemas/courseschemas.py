import logging

import coreapi
import coreschema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Category
from helium.planner.views.apis.schemas.coursegroupschemas import SubCourseGroupListSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class SubCourseListSchema(SubCourseGroupListSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "course",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Category._meta.get_field('course').help_text)
            ),
        ]

        super(SubCourseListSchema, self).__init__(manual_fields=manual_fields)


class CourseIDSchema(BaseIDSchema, SubCourseGroupListSchema):
    def __init__(self):
        super(CourseIDSchema, self).__init__('course')
