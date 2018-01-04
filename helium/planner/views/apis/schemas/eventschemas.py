import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Reminder

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class SubEventListSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "event",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Reminder._meta.get_field('event').help_text)
            ),
        ]

        super(SubEventListSchema, self).__init__(manual_fields=manual_fields)


class EventDetailSchema(BaseIDSchema):
    def __init__(self):
        super(EventDetailSchema, self).__init__('event')
