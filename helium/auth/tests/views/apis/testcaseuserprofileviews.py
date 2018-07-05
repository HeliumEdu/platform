import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from mock import mock
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.services.phoneservice import HeliumPhoneError

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.24'


class TestCaseUserProfileViews(APITestCase):
    def test_user_profile_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('auth_user_profile_detail')),
            self.client.put(reverse('auth_user_profile_detail'))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('helium.common.services.phoneservice.client.api.account.messages.create')
    @mock.patch('helium.auth.serializers.userprofileserializer.verify_number', return_value='+15555555555')
    def test_put_user_profile(self, mock_verify_number, mock_sms_messages_create):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        self.assertIsNone(user.profile.phone)
        self.assertIsNone(user.profile.phone_changing)

        # WHEN
        data = {
            'phone': '(555) 555-5555',
        }
        response = self.client.put(reverse('auth_user_profile_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        mock_verify_number.assert_called_once()
        mock_sms_messages_create.assert_called_once()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['phone'])
        self.assertEqual(response.data['phone_changing'], '+15555555555')
        user = get_user_model().objects.get(pk=user.id)
        self.assertIsNone(user.profile.phone)
        self.assertEqual(user.profile.phone_changing, response.data['phone_changing'])

    @mock.patch('helium.auth.serializers.userprofileserializer.verify_number')
    def test_put_bad_data_fails(self, mock_verify_number):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        self.assertIsNone(user.profile.phone)
        self.assertIsNone(user.profile.phone_changing)
        mock_verify_number.side_effect = HeliumPhoneError('Invalid phone number.')

        # WHEN
        data = {
            'phone': 'not-a-phone',
        }
        response = self.client.put(reverse('auth_user_profile_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

    def test_phone_changes_after_verification(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.profile.phone_changing = '5555555'
        user.profile.phone_verification_code = 123456
        user.profile.save()
        self.assertFalse(user.profile.phone_verified)

        # WHEN
        data = {
            'phone_verification_code': user.profile.phone_verification_code,
        }
        response = self.client.put(reverse('auth_user_profile_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], '5555555')
        self.assertIsNone(response.data['phone_changing'])
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(user.profile.phone, response.data['phone'])
        self.assertIsNone(user.profile.phone_changing)
        self.assertTrue(user.profile.phone_verified)

    def test_remove_phone(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.profile.phone = '5555555'
        user.profile.save()

        # WHEN
        data = {
            'phone': '',
        }
        response = self.client.put(reverse('auth_user_profile_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['phone'], '5555555')
        user = get_user_model().objects.get(pk=user.id)
        self.assertIsNone(user.profile.phone)

    def test_invalid_phone_verification_code_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.profile.phone_changing = '5555555'
        user.profile.phone_verification_code = 123456
        user.profile.save()

        # WHEN
        data = {
            'phone_verification_code': 000000,
        }
        response = self.client.put(reverse('auth_user_profile_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_verification_code', response.data)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        phone_changing = '5555555'
        user.profile.phone_changing = phone_changing
        user.profile.save()

        # WHEN
        data = {
            'phone_changing': '444-4444'
        }
        response = self.client.put(reverse('auth_user_profile_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.profile.phone_changing, phone_changing)
