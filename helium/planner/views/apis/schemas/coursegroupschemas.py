import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Course

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class SubCourseGroupListSchema(AutoSchema):
    """
    If Django Rest Framework adds better support for properly getting the `help_text` of related fields,
    this can be removed
    """
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "course_group",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Course._meta.get_field('course_group').help_text)
            ),
        ]

        super(SubCourseGroupListSchema, self).__init__(manual_fields=manual_fields)


class CourseGroupIDSchema(BaseIDSchema):
    def __init__(self):
        super(CourseGroupIDSchema, self).__init__('course group')
