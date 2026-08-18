import logging

from helium.common.utils.requestid import get_request_id


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or '-'
        return True
