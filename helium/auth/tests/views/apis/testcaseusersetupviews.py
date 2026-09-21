import json
from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums


class TestCaseUserSetupViews(APITestCase):
    def test_user_setup_login_required(self):
        # WHEN
        response = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('helium.auth.services.authservice.import_example_schedule')
    def test_start_setup_dispatches_the_import_once(self, mock_import_schedule):
        # GIVEN
        mock_import_schedule.apply_async = mock.MagicMock()
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        self.assertEqual(user.settings.setup_state, enums.SETUP_PENDING)

        # WHEN
        response1 = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')
        response2 = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data['setup_state'], enums.SETUP_IMPORTING)
        self.assertFalse(response1.data['is_setup_complete'])
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['setup_state'], enums.SETUP_IMPORTING)
        mock_import_schedule.apply_async.assert_called_once()
        self.assertEqual(mock_import_schedule.apply_async.call_args.kwargs['args'], (user.pk,))

    @mock.patch('helium.auth.services.authservice.import_example_schedule')
    def test_start_setup_does_nothing_once_complete(self, mock_import_schedule):
        # GIVEN
        mock_import_schedule.apply_async = mock.MagicMock()
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.setup_state = enums.SETUP_COMPLETE
        user.settings.save()

        # WHEN
        response = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['setup_state'], enums.SETUP_COMPLETE)
        self.assertTrue(response.data['is_setup_complete'])
        mock_import_schedule.apply_async.assert_not_called()

    @mock.patch('helium.auth.services.authservice.import_example_schedule')
    def test_start_setup_applies_regional_at_risk_threshold(self, mock_import_schedule):
        # GIVEN
        mock_import_schedule.apply_async = mock.MagicMock()
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'Europe/Berlin'
        user.settings.save()

        # WHEN
        response = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['at_risk_threshold'], 60)

    def test_start_setup_completes_setup_end_to_end(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['setup_state'], enums.SETUP_COMPLETE)
        user.settings.refresh_from_db()
        self.assertEqual(user.settings.setup_state, enums.SETUP_COMPLETE)
