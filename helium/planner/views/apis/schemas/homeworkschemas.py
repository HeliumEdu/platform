import logging

import coreapi
import coreschema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Reminder
from helium.planner.views.apis.schemas.courseschemas import SubCourseListSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class SubHomeworkListSchema(SubCourseListSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "homework",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Reminder._meta.get_field('homework').help_text)
            ),
        ]

        super(SubHomeworkListSchema, self).__init__(manual_fields=manual_fields)


class HomeworkDetailSchema(BaseIDSchema, SubCourseListSchema):
    def __init__(self):
        super(HomeworkDetailSchema, self).__init__('homework')
