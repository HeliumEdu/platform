import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUserProfileViews(TestCase):
    def test_user_profile_login_required(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk})),
            self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_bad_data_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'phone': '555-5555',
            'phone_carrier': 'invalid'
        }
        response = self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_carrier', response.data)

    def test_put_user_profile(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertIsNone(user.profile.phone)
        self.assertIsNone(user.profile.phone_changing)

        # WHEN
        data = {
            'phone': '555-5555',
            'phone_carrier': 'tmomail.net'
        }
        response = self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['phone'])
        self.assertEqual(response.data['phone_changing'], '5555555')
        user = get_user_model().objects.get(pk=user.id)
        self.assertIsNone(user.profile.phone)
        self.assertEqual(user.profile.phone_changing, response.data['phone_changing'])

    def test_phone_changes_after_verification(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.profile.phone_changing = '5555555'
        user.profile.phone_carrier_changing = 'txt.att.net'
        user.profile.phone_verification_code = 123456
        user.profile.save()
        self.assertFalse(user.profile.phone_verified)

        # WHEN
        data = {
            'phone_verification_code': user.profile.phone_verification_code,
        }
        response = self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], '5555555')
        self.assertIsNone(response.data['phone_changing'])
        self.assertEqual(response.data['phone_carrier'], 'txt.att.net')
        self.assertIsNone(response.data['phone_carrier_changing'])
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(user.profile.phone, response.data['phone'])
        self.assertIsNone(user.profile.phone_changing)
        self.assertEqual(user.profile.phone_carrier, response.data['phone_carrier'])
        self.assertIsNone(user.profile.phone_carrier_changing)
        self.assertTrue(user.profile.phone_verified)

    def test_remove_phone(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.profile.phone = '5555555'
        user.profile.phone_carrier = 'txt.att.net'
        user.profile.save()

        # WHEN
        data = {
            'phone': '',
            'phone_carrier': '',
        }
        response = self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['phone'], '5555555')
        self.assertIsNone(response.data['phone_carrier'])
        user = get_user_model().objects.get(pk=user.id)
        self.assertIsNone(user.profile.phone)
        self.assertIsNone(user.profile.phone_carrier)

    def test_invalid_phone_verification_code_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.profile.phone_changing = '5555555'
        user.profile.phone_verification_code = 123456
        user.profile.save()

        # WHEN
        data = {
            'phone_verification_code': 000000,
        }
        response = self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_verification_code', response.data)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        phone_changing = '5555555'
        user.profile.phone_changing = phone_changing
        user.profile.save()

        # WHEN
        data = {
            'phone_changing': '444-4444'
        }
        response = self.client.put(reverse('api_auth_users_profile_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.profile.phone_changing, phone_changing)
