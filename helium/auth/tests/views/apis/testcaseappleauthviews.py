__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from firebase_admin import auth as firebase_auth

from helium.auth.tests.helpers import userhelper


class TestCaseAppleAuthViews(APITestCase):
    @patch('helium.auth.serializers.userserializer.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_creates_new_user(self, mock_verify_token, mock_import_schedule):
        """Test that Apple login creates a new user and returns tokens."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'apple-user-123',
            'email': 'newuser@icloud.com',
            'email_verified': True
        }
        mock_import_schedule.delay = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify user was created
        user = get_user_model().objects.get(email='newuser@icloud.com')
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, 'newuser@icloud.com')
        self.assertFalse(user.has_usable_password())

        # Verify username was generated from email
        self.assertTrue(user.username.startswith('newuser'))

        # Verify example schedule import was triggered
        mock_import_schedule.delay.assert_called_once_with(user.pk)

        # Verify tokens were created
        self.assertEqual(OutstandingToken.objects.count(), 1)

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_existing_user(self, mock_verify_token):
        """Test that Apple login logs in an existing user."""
        # GIVEN
        existing_user = userhelper.given_a_user_exists(
            username='existing_user',
            email='existing@icloud.com'
        )
        mock_verify_token.return_value = {
            'uid': 'apple-user-456',
            'email': 'existing@icloud.com',
            'email_verified': True
        }

        # WHEN
        data = {'id_token': 'valid-firebase-id-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify no new user was created
        self.assertEqual(get_user_model().objects.filter(email='existing@icloud.com').count(), 1)

        # Verify same user
        user = get_user_model().objects.get(email='existing@icloud.com')
        self.assertEqual(user.pk, existing_user.pk)

    @patch('helium.auth.serializers.userserializer.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_username_collision_handling(self, mock_verify_token, mock_import_schedule):
        """Test that username collisions are handled correctly."""
        # GIVEN
        # Create a user with username 'testuser'
        userhelper.given_a_user_exists(username='testuser', email='other@example.com')

        mock_verify_token.return_value = {
            'uid': 'apple-user-789',
            'email': 'testuser@icloud.com',
            'email_verified': True
        }
        mock_import_schedule.delay = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify new user was created with incremented username
        new_user = get_user_model().objects.get(email='testuser@icloud.com')
        self.assertNotEqual(new_user.username, 'testuser')  # Should be 'testuser1'
        self.assertTrue(new_user.username.startswith('testuser'))

    def test_apple_login_missing_id_token(self):
        """Test that missing id_token returns error."""
        # WHEN
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps({}),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id_token', str(response.data))

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_invalid_token(self, mock_verify_token):
        """Test that invalid Firebase ID token returns error."""
        # GIVEN
        mock_verify_token.side_effect = firebase_auth.InvalidIdTokenError('Invalid token')

        # WHEN
        data = {'id_token': 'invalid-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Invalid', str(response.data))

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_expired_token(self, mock_verify_token):
        """Test that expired Firebase ID token returns error."""
        # GIVEN
        mock_verify_token.side_effect = firebase_auth.ExpiredIdTokenError(
            'Token expired',
            cause=Exception('Token expired')
        )

        # WHEN
        data = {'id_token': 'expired-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('expired', str(response.data).lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_email_not_verified(self, mock_verify_token):
        """Test that unverified email returns error."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'apple-user-999',
            'email': 'unverified@icloud.com',
            'email_verified': False
        }

        # WHEN
        data = {'id_token': 'valid-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('verified', str(response.data).lower())

        # Verify no user was created
        self.assertFalse(get_user_model().objects.filter(email='unverified@icloud.com').exists())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_no_email_in_token(self, mock_verify_token):
        """Test that missing email in token returns error."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'apple-user-000',
            'email_verified': True
            # Note: no 'email' field
        }

        # WHEN
        data = {'id_token': 'valid-token'}
        response = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Email', str(response.data))

    @patch('helium.auth.serializers.userserializer.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_user_has_no_usable_password(self, mock_verify_token, mock_import_schedule):
        """Test that users created via Apple Sign-In cannot use password login."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'apple-user-pass-test',
            'email': 'nopass@icloud.com',
            'email_verified': True
        }
        mock_import_schedule.delay = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token'}
        self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        user = get_user_model().objects.get(email='nopass@icloud.com')
        self.assertFalse(user.has_usable_password())

        # Verify they cannot login with password
        login_response = self.client.post(
            reverse('auth_token_obtain'),
            json.dumps({'username': user.username, 'password': 'any-password'}),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('helium.auth.serializers.userserializer.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_apple_login_multiple_times_same_user(self, mock_verify_token, mock_import_schedule):
        """Test that logging in multiple times with same Apple account works."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'apple-user-repeat',
            'email': 'repeat@icloud.com',
            'email_verified': True
        }
        mock_import_schedule.delay = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token'}
        response1 = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )
        response2 = self.client.post(
            reverse('auth_apple_login'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Verify only one user exists
        self.assertEqual(get_user_model().objects.filter(email='repeat@icloud.com').count(), 1)

        # Verify different tokens were generated
        self.assertNotEqual(response1.data['access'], response2.data['access'])

        # Verify example schedule only imported once (on first login)
        self.assertEqual(mock_import_schedule.delay.call_count, 1)
