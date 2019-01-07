import logging

from helium.common.schemas import BaseIDSchema

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class ExternalCalendarIDSchema(BaseIDSchema):
    def __init__(self):
        super().__init__('external calendar')
