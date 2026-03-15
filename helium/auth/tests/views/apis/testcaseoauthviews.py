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

from helium.auth.models import UserOAuthProvider
from helium.auth.tests.helpers import userhelper


class TestCaseOAuthViews(APITestCase):
    """Tests for the unified OAuth login endpoint."""

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_creates_new_user_google(self, mock_verify_token, mock_import_schedule):
        """Test that Google OAuth login creates a new user and returns tokens."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'google-user-123',
            'email': 'newuser@gmail.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify user was created
        user = get_user_model().objects.get(email='newuser@gmail.com')
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, 'newuser@gmail.com')
        self.assertFalse(user.has_usable_password())

        # Verify username was generated from email
        self.assertTrue(user.username.startswith('newuser'))

        # Verify example schedule import was triggered
        mock_import_schedule.apply_async.assert_called_once()
        call_args = mock_import_schedule.apply_async.call_args
        self.assertEqual(call_args.kwargs['args'], (user.pk,))

        # Verify tokens were created
        self.assertEqual(OutstandingToken.objects.count(), 1)

        # Verify OAuth provider was created
        oauth_provider = UserOAuthProvider.objects.get(user=user, provider='google')
        self.assertEqual(oauth_provider.provider_user_id, 'google-user-123')

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_creates_new_user_apple(self, mock_verify_token, mock_import_schedule):
        """Test that Apple OAuth login creates a new user and returns tokens."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'apple-user-123',
            'email': 'newuser@icloud.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'apple'}
        response = self.client.post(
            reverse('auth_token_oauth'),
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
        self.assertFalse(user.has_usable_password())

        # Verify OAuth provider was created
        oauth_provider = UserOAuthProvider.objects.get(user=user, provider='apple')
        self.assertEqual(oauth_provider.provider_user_id, 'apple-user-123')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_existing_user(self, mock_verify_token):
        """Test that OAuth login logs in an existing user."""
        # GIVEN
        existing_user = userhelper.given_a_user_exists(
            username='existing_user',
            email='existing@gmail.com'
        )
        mock_verify_token.return_value = {
            'uid': 'google-user-456',
            'email': 'existing@gmail.com',
            'email_verified': True
        }

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify no new user was created
        self.assertEqual(get_user_model().objects.filter(email='existing@gmail.com').count(), 1)

        # Verify same user
        user = get_user_model().objects.get(email='existing@gmail.com')
        self.assertEqual(user.pk, existing_user.pk)

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_username_collision_handling(self, mock_verify_token, mock_import_schedule):
        """Test that username collisions are handled correctly."""
        # GIVEN
        userhelper.given_a_user_exists(username='testuser', email='other@example.com')

        mock_verify_token.return_value = {
            'uid': 'google-user-789',
            'email': 'testuser@gmail.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify new user was created with incremented username
        new_user = get_user_model().objects.get(email='testuser@gmail.com')
        self.assertNotEqual(new_user.username, 'testuser')
        self.assertTrue(new_user.username.startswith('testuser'))

    def test_oauth_login_missing_id_token(self):
        """Test that missing id_token returns error."""
        # WHEN
        data = {'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id_token', str(response.data))

    def test_oauth_login_missing_provider(self):
        """Test that missing provider returns error."""
        # WHEN
        data = {'id_token': 'valid-token'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('provider', str(response.data))

    def test_oauth_login_invalid_provider(self):
        """Test that invalid provider returns error."""
        # WHEN
        data = {'id_token': 'valid-token', 'provider': 'facebook'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('provider', str(response.data).lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_invalid_token(self, mock_verify_token):
        """Test that invalid Firebase ID token returns error."""
        # GIVEN
        mock_verify_token.side_effect = firebase_auth.InvalidIdTokenError('Invalid token')

        # WHEN
        data = {'id_token': 'invalid-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Invalid', str(response.data))

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_expired_token(self, mock_verify_token):
        """Test that expired Firebase ID token returns error."""
        # GIVEN
        mock_verify_token.side_effect = firebase_auth.ExpiredIdTokenError(
            'Token expired',
            cause=Exception('Token expired')
        )

        # WHEN
        data = {'id_token': 'expired-token', 'provider': 'apple'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('expired', str(response.data).lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_email_not_verified(self, mock_verify_token):
        """Test that unverified email returns error."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'google-user-999',
            'email': 'unverified@gmail.com',
            'email_verified': False
        }

        # WHEN
        data = {'id_token': 'valid-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('verified', str(response.data).lower())

        # Verify no user was created
        self.assertFalse(get_user_model().objects.filter(email='unverified@gmail.com').exists())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_no_email_in_token(self, mock_verify_token):
        """Test that missing email in token returns error."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'google-user-000',
            'email_verified': True
        }

        # WHEN
        data = {'id_token': 'valid-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Email', str(response.data))

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_user_has_no_usable_password(self, mock_verify_token, mock_import_schedule):
        """Test that users created via OAuth cannot use password login."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'google-user-pass-test',
            'email': 'nopass@gmail.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        user = get_user_model().objects.get(email='nopass@gmail.com')
        self.assertFalse(user.has_usable_password())

        # Verify they cannot login with password
        login_response = self.client.post(
            reverse('auth_token_obtain'),
            json.dumps({'username': user.username, 'password': 'any-password'}),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_multiple_times_same_user(self, mock_verify_token, mock_import_schedule):
        """Test that logging in multiple times with same account works."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'google-user-repeat',
            'email': 'repeat@gmail.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response1 = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )
        response2 = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Verify only one user exists
        self.assertEqual(get_user_model().objects.filter(email='repeat@gmail.com').count(), 1)

        # Verify different tokens were generated
        self.assertNotEqual(response1.data['access'], response2.data['access'])

        # Verify example schedule only imported once (on first login)
        self.assertEqual(mock_import_schedule.apply_async.call_count, 1)

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_updates_provider_last_used(self, mock_verify_token):
        """Test that subsequent logins update the OAuth provider's last_used_at."""
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'google-uid-456',
            'email': 'existing@gmail.com',
            'email_verified': True
        }

        # Create initial login
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        user = get_user_model().objects.get(email='existing@gmail.com')
        oauth_provider = UserOAuthProvider.objects.get(user=user, provider='google')
        first_last_used = oauth_provider.last_used_at

        # WHEN - login again
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify OAuth provider was updated (not duplicated)
        self.assertEqual(UserOAuthProvider.objects.filter(user=user, provider='google').count(), 1)

        oauth_provider.refresh_from_db()
        self.assertGreater(oauth_provider.last_used_at, first_last_used)

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_user_can_have_multiple_oauth_providers(self, mock_verify_token, mock_import_schedule):
        """Test that a user can link both Google and Apple OAuth providers."""
        # GIVEN - user logs in with Google first
        mock_verify_token.return_value = {
            'uid': 'google-uid-multi',
            'email': 'multiauth@gmail.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        user = get_user_model().objects.get(email='multiauth@gmail.com')

        # WHEN - same user logs in with Apple
        mock_verify_token.return_value = {
            'uid': 'apple-uid-multi',
            'email': 'multiauth@gmail.com',
            'email_verified': True
        }

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'apple'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user has both OAuth providers
        oauth_providers = UserOAuthProvider.objects.filter(user=user)
        self.assertEqual(oauth_providers.count(), 2)

        google_provider = oauth_providers.get(provider='google')
        apple_provider = oauth_providers.get(provider='apple')

        self.assertEqual(google_provider.provider_user_id, 'google-uid-multi')
        self.assertEqual(apple_provider.provider_user_id, 'apple-uid-multi')

        # Verify example schedule only imported once (on first provider link)
        self.assertEqual(mock_import_schedule.apply_async.call_count, 1)

    def test_oauth_login_provider_case_insensitive(self):
        """Test that provider field is case-insensitive."""
        # WHEN
        data = {'id_token': 'valid-token', 'provider': 'GOOGLE'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN - Should fail on token validation, not provider validation
        # This means 'GOOGLE' was accepted as a valid provider
        self.assertNotIn('provider', str(response.data).lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_activates_inactive_user(self, mock_verify_token):
        """Test that OAuth login activates an existing inactive user."""
        # GIVEN - user registered via email but hasn't verified
        inactive_user = userhelper.given_an_inactive_user_exists(
            username='inactive_user',
            email='inactive@gmail.com'
        )
        self.assertFalse(inactive_user.is_active)

        mock_verify_token.return_value = {
            'uid': 'google-user-inactive',
            'email': 'inactive@gmail.com',
            'email_verified': True
        }

        # WHEN - user logs in via OAuth
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN - login succeeds and user is activated
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify user was activated
        inactive_user.refresh_from_db()
        self.assertTrue(inactive_user.is_active)

        # Verify OAuth provider was linked
        oauth_provider = UserOAuthProvider.objects.get(user=inactive_user, provider='google')
        self.assertEqual(oauth_provider.provider_user_id, 'google-user-inactive')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_conflict_uid_linked_to_different_user(self, mock_verify_token):
        """Test that OAuth login fails when UID is linked to a different user than email lookup finds."""
        # GIVEN - user A with Google OAuth linked
        user_a = userhelper.given_a_user_exists(username='user_a', email='user_a@gmail.com')
        UserOAuthProvider.objects.create(
            user=user_a,
            provider='google',
            provider_user_id='shared-google-uid',
        )

        # AND - user B with a different email (no OAuth)
        userhelper.given_a_user_exists(username='user_b', email='user_b@gmail.com')

        # WHEN - Someone tries to login with user A's Google UID but user B's email
        # (This shouldn't happen normally, but could indicate bad data or attack)
        mock_verify_token.return_value = {
            'uid': 'shared-google-uid',  # Linked to user_a
            'email': 'user_b@gmail.com',  # Belongs to user_b
            'email_verified': True
        }

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN - Should fail with account conflict error
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('account conflict', response.data['detail'].lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_updates_uid_when_firebase_user_recreated(self, mock_verify_token):
        """Test that OAuth login updates the provider UID when the Firebase user was recreated.

        This handles the case where a user's Firebase account was deleted and recreated,
        resulting in a new UID for the same email/provider combination.
        """
        # GIVEN - existing user with Google OAuth linked to old UID
        existing_user = userhelper.given_a_user_exists(
            username='recreated_user',
            email='recreated@gmail.com'
        )
        old_oauth = UserOAuthProvider.objects.create(
            user=existing_user,
            provider='google',
            provider_user_id='old-firebase-uid-123',
        )
        old_last_used = old_oauth.last_used_at

        # WHEN - user logs in with same email but different UID (Firebase user was recreated)
        mock_verify_token.return_value = {
            'uid': 'new-firebase-uid-456',  # Different UID
            'email': 'recreated@gmail.com',  # Same email
            'email_verified': True
        }

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN - login succeeds
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Verify the OAuth provider UID was updated (not duplicated)
        oauth_providers = UserOAuthProvider.objects.filter(user=existing_user, provider='google')
        self.assertEqual(oauth_providers.count(), 1)

        updated_oauth = oauth_providers.first()
        self.assertEqual(updated_oauth.provider_user_id, 'new-firebase-uid-456')
        self.assertGreater(updated_oauth.last_used_at, old_last_used)
