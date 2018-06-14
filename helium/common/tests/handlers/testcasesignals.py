from django.test import TestCase
from mock import mock

from helium.common.services.phoneservice import HeliumPhoneError
from helium.common.tasks import send_text

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.21'


class TestCaseSignals(TestCase):
    @mock.patch('helium.common.tasks.send_sms')
    def test_task_failure_signal(self, mock_send_sms):
        # GIVEN
        mock_send_sms.side_effect = HeliumPhoneError('Invalid phone number.')

        # WHEN
        # send_text.delay('+15555555555', 'A text that will not send.')

        # THEN

