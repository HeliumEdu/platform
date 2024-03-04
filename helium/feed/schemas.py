__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from helium.common.schemas import BaseIDSchema

logger = logging.getLogger(__name__)


class ExternalCalendarIDSchema(BaseIDSchema):
    def __init__(self):
        super().__init__('external calendar')
