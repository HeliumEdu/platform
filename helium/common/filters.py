__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import logging

from helium.common.utils.requestid import get_request_id


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or '-'
        return True
