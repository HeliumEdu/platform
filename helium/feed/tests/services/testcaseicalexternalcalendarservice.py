__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.test import TestCase

from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError

logger = logging.getLogger(__name__)


class TestCaseICALExternalCalendarService(TestCase):
    def test_validate_url_file_invalid(self):
        # GIVEN
        with self.assertRaises(HeliumICalError) as ctx:
            icalexternalcalendarservice.validate_url("file://some_local_file.txt")
        self.assertEqual(str(ctx.exception), 'Enter a valid URL.')
