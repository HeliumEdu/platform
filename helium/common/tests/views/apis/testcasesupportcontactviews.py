from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from helium.common.tests.helpers import supportcontacthelper
from helium.common.tests.helpers.supportcontacthelper import SUBMITTER_EMAIL, jsm_error, sent_payload
from helium.common.tests.test import CacheTestCase

SPAM_REPORTER_EMAIL = 'support+spam@heliumedu.com'


@override_settings(DISABLE_EMAILS=False, ADMIN_EMAIL_ADDRESS='support@heliumedu.com')
@mock.patch('helium.common.views.apis.supportcontactview.clear_ses_suppression_if_exists')
@mock.patch('helium.common.services.jsmservice.urlopen_secure')
class TestCaseSupportContactViews(CacheTestCase):
    def test_submit(self, mock_urlopen, mock_clear_ses):
        # GIVEN
        supportcontacthelper.given_jsm_responds(mock_urlopen, {'issueKey': 'HS-1'})

        # WHEN
        response = self.client.post(reverse('support_contact'), supportcontacthelper.given_a_submission())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = sent_payload(mock_urlopen)
        self.assertEqual(payload['raiseOnBehalfOf'], SUBMITTER_EMAIL)
        self.assertEqual(payload['requestTypeId'], '2')
        self.assertEqual(payload['requestFieldValues']['summary'], 'Bug Report: Planner shows tasks a day early')
        mock_clear_ses.assert_called_once_with(SUBMITTER_EMAIL)

    def test_submit_with_attachment(self, mock_urlopen, mock_clear_ses):
        # GIVEN
        supportcontacthelper.given_jsm_responds(mock_urlopen,
                                                {'issueKey': 'HS-1'},
                                                {'temporaryAttachments': [{'temporaryAttachmentId': 'temp-1'}]},
                                                {})
        attachment = SimpleUploadedFile('screenshot.png', b'png-bytes', content_type='image/png')

        # WHEN
        response = self.client.post(reverse('support_contact'),
                                    supportcontacthelper.given_a_submission(attachment=attachment))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_urlopen.call_count, 3)
        self.assertIn(b'png-bytes', mock_urlopen.call_args_list[1][0][0].data)
        self.assertEqual(sent_payload(mock_urlopen, 2)['temporaryAttachmentIds'], ['temp-1'])

    def test_honeypot(self, mock_urlopen, mock_clear_ses):
        # WHEN
        response = self.client.post(reverse('support_contact'),
                                    supportcontacthelper.given_a_submission(website='http://bot.example'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_urlopen.assert_not_called()
        mock_clear_ses.assert_not_called()

    def test_jsm_failure(self, mock_urlopen, mock_clear_ses):
        # GIVEN
        supportcontacthelper.given_jsm_responds(mock_urlopen, jsm_error())

        # WHEN
        response = self.client.post(reverse('support_contact'), supportcontacthelper.given_a_submission())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @mock.patch('helium.common.views.apis.supportcontactview.metricutils.increment')
    def test_suspected_spam_quarantined(self, mock_increment, mock_urlopen, mock_clear_ses):
        # GIVEN
        supportcontacthelper.given_jsm_responds(mock_urlopen, {'issueKey': 'HS-2'})

        # WHEN
        response = self.client.post(reverse('support_contact'), supportcontacthelper.given_a_spam_submission())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'ok': True})
        payload = sent_payload(mock_urlopen)
        self.assertEqual(payload['raiseOnBehalfOf'], SPAM_REPORTER_EMAIL)
        self.assertEqual(payload['requestTypeId'], '2')
        self.assertIn(f'Submitter: {SUBMITTER_EMAIL}', payload['requestFieldValues']['description'])
        mock_increment.assert_any_call('action.support_contact.suspected_spam')
        mock_increment.assert_any_call('action.support_contact.quarantine.sent')
        mock_clear_ses.assert_called_once_with(SUBMITTER_EMAIL)

    @mock.patch('helium.common.services.jsmservice.metricutils.increment')
    def test_quarantine_failure_falls_back(self, mock_increment, mock_urlopen, mock_clear_ses):
        # GIVEN
        supportcontacthelper.given_jsm_responds(mock_urlopen, jsm_error(), {'issueKey': 'HS-3'})

        # WHEN
        response = self.client.post(reverse('support_contact'), supportcontacthelper.given_a_spam_submission())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(sent_payload(mock_urlopen, 0)['raiseOnBehalfOf'], SPAM_REPORTER_EMAIL)
        self.assertEqual(sent_payload(mock_urlopen, 1)['raiseOnBehalfOf'], SUBMITTER_EMAIL)
        mock_increment.assert_any_call('action.support_contact.quarantine.failed')
        mock_increment.assert_any_call('action.support_contact.sent')
        self.assertNotIn(mock.call('action.support_contact.failed'), mock_increment.call_args_list)

    def test_quarantine_attachment_failure_does_not_fall_back(self, mock_urlopen, mock_clear_ses):
        # GIVEN
        supportcontacthelper.given_jsm_responds(mock_urlopen, {'issueKey': 'HS-4'}, jsm_error())
        attachment = SimpleUploadedFile('screenshot.png', b'png-bytes', content_type='image/png')

        # WHEN
        response = self.client.post(reverse('support_contact'),
                                    supportcontacthelper.given_a_spam_submission(attachment=attachment))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(sent_payload(mock_urlopen)['raiseOnBehalfOf'], SPAM_REPORTER_EMAIL)
