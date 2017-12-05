"""
Tests for UserProfile interaction.
"""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper
from helium.auth.utils.userutils import generate_phone_verification_code

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUserProfile(TestCase):
    def test_user_profile_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self.client.get(reverse('api_user_profile'))

        # THEN
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login?next={}'.format(reverse('api_user_profile')))

    def test_get_user_profile(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        response = self.client.get(reverse('api_user_profile'))

        # THEN
        self.assertNotIn('phone_verification_code', response.data)
        self.assertEqual(user.profile.phone, response.data['phone'])
        self.assertEqual(user.profile.phone_carrier, response.data['phone_carrier'])
        self.assertEqual(user.profile.user.pk, response.data['user'])

    def test_put_bad_data_fails(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'phone': '555-5555',
            'phone_carrier': 'invalid'
        }
        response = self.client.put(reverse('api_user_profile'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 400)
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
        response = self.client.put(reverse('api_user_profile'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertIsNone(response.data['phone'])
        self.assertEqual(response.data['phone_changing'], '555-5555')
        user = get_user_model().objects.get(id=user.id)
        self.assertIsNone(user.profile.phone)
        self.assertEqual(user.profile.phone_changing, response.data['phone_changing'])

    def test_phone_changes_after_verification(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.profile.phone_changing = '555-5555'
        user.profile.phone_verification_code = 123456
        user.profile.save()
        self.assertFalse(user.profile.phone_verified)

        # WHEN
        data = {
            'phone_verification_code': user.profile.phone_verification_code,
        }
        response = self.client.put(reverse('api_user_profile'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.data['phone'], '555-5555')
        self.assertIsNone(response.data['phone_changing'])
        user = get_user_model().objects.get(id=user.id)
        self.assertEqual(user.profile.phone, response.data['phone'])
        self.assertIsNone(user.profile.phone_changing)
        self.assertTrue(user.profile.phone_verified)

    def test_invalid_phone_verification_code_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.profile.phone_changing = '555-5555'
        user.profile.phone_verification_code = 123456
        user.profile.save()

        # WHEN
        data = {
            'phone_verification_code': 000000,
        }
        response = self.client.put(reverse('api_user_profile'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_verification_code', response.data)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        phone_changing = '555-5555'
        user.profile.phone_changing = phone_changing
        user.profile.save()

        # WHEN
        data = {
            'phone_changing': '444-4444'
        }
        response = self.client.put(reverse('api_user_profile'), json.dumps(data), content_type='application/json')

        # THEN
        user = get_user_model().objects.get(id=user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.profile.phone_changing, phone_changing)
