import logging

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendarIDSchema(BaseIDSchema):
    def __init__(self):
        super(ExternalCalendarIDSchema, self).__init__('external calendar')
