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


class EventDetailSchema(BaseIDSchema):
    def __init__(self):
        super(EventDetailSchema, self).__init__('event')
