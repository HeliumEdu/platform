__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.5"

import logging


class IgnoreStatusCheckFilter(logging.Filter):
    def filter(self, record):
        return "/status/" not in record.getMessage()
