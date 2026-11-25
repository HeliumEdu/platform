import json
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone, translation
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import UnavailableError

from helium.auth.models import UserOAuthProvider, UserSettings
from helium.auth.tests.helpers import userhelper
from helium.common import enums


class TestCaseOAuthViews(APITestCase):
    def setUp(self):
        self.mock_get_user = self.enterContext(patch('helium.auth.services.authservice.firebase_auth.get_user',
                                                     side_effect=UnavailableError('Firebase unavailable')))

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_creates_new_user_google(self, mock_verify_token, mock_import_schedule):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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
            content_type='application/json',
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

        # Setup waits for the app to start it, so the account is still pending
        mock_import_schedule.apply_async.assert_not_called()
        self.assertEqual(user.settings.setup_state, enums.SETUP_PENDING)

        # Verify tokens were created
        self.assertEqual(OutstandingToken.objects.count(), 1)

        # Verify OAuth provider was created
        oauth_provider = UserOAuthProvider.objects.get(user=user, provider='google')
        self.assertEqual(oauth_provider.provider_user_id, 'google-user-123')

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_creates_new_user_apple(self, mock_verify_token, mock_import_schedule):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'apple.com'},
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
        # GIVEN
        existing_user = userhelper.given_a_user_exists(
            username='existing_user',
            email='existing@gmail.com'
        )
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_fails_when_user_pending_deletion(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_a_user_exists(
            username='existing_user',
            email='existing@gmail.com',
        )
        UserOAuthProvider.objects.create(
            user=existing_user,
            provider='google',
            provider_user_id='google-user-789',
        )
        existing_user.deletion_requested_at = timezone.now()
        existing_user.save(update_fields=['deletion_requested_at'])

        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'google-user-789',
            'email': 'existing@gmail.com',
            'email_verified': True,
        }

        # WHEN
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps({'id_token': 'valid-firebase-id-token', 'provider': 'google'}),
            content_type='application/json',
        )

        # THEN
        self.assertContains(response, 'Please wait a moment and try again',
                            status_code=status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.filter(email='existing@gmail.com').count(), 1)

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_username_collision_handling(self, mock_verify_token, mock_import_schedule):
        # GIVEN
        userhelper.given_a_user_exists(username='testuser', email='other@example.com')

        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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
        self.assertEqual(response.data['detail'], 'Sign in with Google failed. Please try again.')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_expired_token(self, mock_verify_token):
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
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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
        self.assertEqual(response.data['detail'], "Google didn't share this account's email address.")

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_user_has_no_usable_password(self, mock_verify_token, mock_import_schedule):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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
            json.dumps({'email': user.email, 'password': 'any-password'}),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_multiple_times_same_user(self, mock_verify_token, mock_import_schedule):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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
            content_type='application/json',
        )
        response2 = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json',
        )

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Verify only one user exists
        self.assertEqual(get_user_model().objects.filter(email='repeat@gmail.com').count(), 1)

        # Verify different tokens were generated
        self.assertNotEqual(response1.data['access'], response2.data['access'])

        # Setup waits for the app to start it
        mock_import_schedule.apply_async.assert_not_called()

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_updates_provider_last_used(self, mock_verify_token):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
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

        # WHEN
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
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'google-uid-multi',
            'email': 'multiauth@gmail.com',
            'email_verified': True
        }
        mock_import_schedule.apply_async = MagicMock()

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json',
        )

        user = get_user_model().objects.get(email='multiauth@gmail.com')

        # WHEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'apple.com'},
            'uid': 'apple-uid-multi',
            'email': 'multiauth@gmail.com',
            'email_verified': True
        }

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'apple'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json',
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

        # Setup waits for the app to start it
        mock_import_schedule.apply_async.assert_not_called()

    def test_oauth_login_provider_case_insensitive(self):
        # WHEN
        data = {'id_token': 'valid-token', 'provider': 'GOOGLE'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json',
        )

        # THEN
        self.assertNotIn('provider', str(response.data).lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_activates_inactive_user(self, mock_verify_token):
        # GIVEN
        inactive_user = userhelper.given_an_inactive_user_exists(
            username='inactive_user',
            email='inactive@gmail.com'
        )
        self.assertFalse(inactive_user.is_active)

        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'google-user-inactive',
            'email': 'inactive@gmail.com',
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

        # Verify user was activated
        inactive_user.refresh_from_db()
        self.assertTrue(inactive_user.is_active)

        # Verify OAuth provider was linked
        oauth_provider = UserOAuthProvider.objects.get(user=inactive_user, provider='google')
        self.assertEqual(oauth_provider.provider_user_id, 'google-user-inactive')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_conflict_uid_linked_to_different_user(self, mock_verify_token):
        # GIVEN
        user_a = userhelper.given_a_user_exists(username='user_a', email='user_a@gmail.com')
        UserOAuthProvider.objects.create(
            user=user_a,
            provider='google',
            provider_user_id='shared-google-uid',
        )

        # AND - user B with a different email (no OAuth)
        userhelper.given_a_user_exists(username='user_b', email='user_b@gmail.com')

        # WHEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'shared-google-uid',
            'email': 'user_b@gmail.com',
            'email_verified': True
        }

        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('account conflict', response.data['detail'].lower())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_updates_uid_when_firebase_user_recreated(self, mock_verify_token):
        # GIVEN
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

        # WHEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'new-firebase-uid-456',
            'email': 'recreated@gmail.com',
            'email_verified': True
        }

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

        # Verify the OAuth provider UID was updated (not duplicated)
        oauth_providers = UserOAuthProvider.objects.filter(user=existing_user, provider='google')
        self.assertEqual(oauth_providers.count(), 1)

        updated_oauth = oauth_providers.first()
        self.assertEqual(updated_oauth.provider_user_id, 'new-firebase-uid-456')
        self.assertGreater(updated_oauth.last_used_at, old_last_used)

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_rejects_token_from_different_provider(self, mock_verify_token):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'microsoft.com'},
            'uid': 'microsoft-uid',
            'email': 'someone@gmail.com',
            'email_verified': False
        }

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'google'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(get_user_model().objects.filter(email='someone@gmail.com').exists())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_rejects_token_without_sign_in_provider(self, mock_verify_token):
        # GIVEN
        mock_verify_token.return_value = {
            'uid': 'some-uid',
            'email': 'someone@gmail.com',
            'email_verified': False
        }

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'microsoft'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(get_user_model().objects.filter(email='someone@gmail.com').exists())

    @patch('helium.auth.services.authservice.import_example_schedule')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_creates_new_user_microsoft_unverified_email(self, mock_verify_token, mock_import_schedule):
        # GIVEN
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'microsoft.com'},
            'uid': 'microsoft-uid-new',
            'email': 'newuser@gmail.com',
            'email_verified': False
        }
        mock_import_schedule.apply_async = MagicMock()

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'microsoft'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = get_user_model().objects.get(email='newuser@gmail.com')
        self.assertEqual(UserOAuthProvider.objects.get(user=user).provider, 'microsoft')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_microsoft_unverified_email_cannot_claim_existing_account(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_an_inactive_user_exists(username='existing', email='existing@gmail.com')
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'microsoft.com'},
            'uid': 'microsoft-uid-unlinked',
            'email': 'existing@gmail.com',
            'email_verified': False
        }

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'microsoft'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already registered with a different sign-in method', str(response.data))
        self.assertNotIn('access', response.data)
        self.assertFalse(UserOAuthProvider.objects.filter(user=existing_user).exists())
        existing_user.refresh_from_db()
        self.assertFalse(existing_user.is_active)

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_microsoft_unverified_email_links_when_firebase_user_already_linked(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_a_user_exists(username='existing', email='existing@gmail.com')
        UserOAuthProvider.objects.create(user=existing_user, provider='google', provider_user_id='shared-firebase-uid')
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'microsoft.com'},
            'uid': 'shared-firebase-uid',
            'email': 'existing@gmail.com',
            'email_verified': False
        }

        # WHEN
        data = {'id_token': 'valid-firebase-id-token', 'provider': 'microsoft'}
        response = self.client.post(
            reverse('auth_token_oauth'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(UserOAuthProvider.objects.filter(user=existing_user).values_list('provider', flat=True)),
            {'google', 'microsoft'})

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_unlinks_providers_firebase_dropped(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_a_user_exists(username='existing', email='existing@gmail.com')
        UserOAuthProvider.objects.create(user=existing_user, provider='microsoft', provider_user_id='firebase-uid')
        UserOAuthProvider.objects.create(user=existing_user, provider='google', provider_user_id='firebase-uid')
        self.mock_get_user.side_effect = None
        self.mock_get_user.return_value = MagicMock(provider_data=[MagicMock(provider_id='google.com')])
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'firebase-uid',
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
        self.mock_get_user.assert_called_once_with('firebase-uid')
        self.assertEqual(list(UserOAuthProvider.objects.filter(user=existing_user).values_list('provider', flat=True)),
                         ['google'])
        self.assertEqual(response.data['unlinked_providers'], ['microsoft'])

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_links_providers_firebase_added(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_a_user_exists(username='existing', email='existing@gmail.com')
        UserOAuthProvider.objects.create(user=existing_user, provider='google', provider_user_id='firebase-uid')
        self.mock_get_user.side_effect = None
        self.mock_get_user.return_value = MagicMock(provider_data=[MagicMock(provider_id='google.com'),
                                                                   MagicMock(provider_id='microsoft.com'),
                                                                   MagicMock(provider_id='password')])
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'firebase-uid',
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
        microsoft_provider = UserOAuthProvider.objects.get(user=existing_user, provider='microsoft')
        self.assertEqual(microsoft_provider.provider_user_id, 'firebase-uid')
        self.assertEqual(UserOAuthProvider.objects.filter(user=existing_user).count(), 2,
                         'non-OAuth Firebase providers are not linked')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_keeps_providers_when_firebase_lookup_fails(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_a_user_exists(username='existing', email='existing@gmail.com')
        UserOAuthProvider.objects.create(user=existing_user, provider='microsoft', provider_user_id='firebase-uid')
        UserOAuthProvider.objects.create(user=existing_user, provider='google', provider_user_id='firebase-uid')
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'firebase-uid',
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
        self.assertEqual(UserOAuthProvider.objects.filter(user=existing_user).count(), 2)

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_skips_firebase_provider_linked_to_another_user(self, mock_verify_token):
        # GIVEN
        existing_user = userhelper.given_a_user_exists(username='existing', email='existing@gmail.com')
        UserOAuthProvider.objects.create(user=existing_user, provider='google', provider_user_id='firebase-uid')
        other_user = userhelper.given_a_user_exists(username='other', email='other@gmail.com')
        UserOAuthProvider.objects.create(user=other_user, provider='microsoft', provider_user_id='firebase-uid')
        self.mock_get_user.side_effect = None
        self.mock_get_user.return_value = MagicMock(provider_data=[MagicMock(provider_id='google.com'),
                                                                   MagicMock(provider_id='microsoft.com')])
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': 'firebase-uid',
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
        self.assertEqual(list(UserOAuthProvider.objects.filter(user=existing_user).values_list('provider', flat=True)),
                         ['google'])
        self.assertTrue(UserOAuthProvider.objects.filter(user=other_user, provider='microsoft').exists())

    def _given_new_google_user(self, mock_verify_token, email):
        mock_verify_token.return_value = {
            'firebase': {'sign_in_provider': 'google.com'},
            'uid': f'uid-{email}',
            'email': email,
            'email_verified': True
        }

    @patch('helium.auth.tasks.commonutils.send_multipart_email')
    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_saves_the_language_of_a_new_user_before_the_welcome_email(self, mock_verify_token,
                                                                                   mock_send):
        # GIVEN
        self._given_new_google_user(mock_verify_token, 'lang@gmail.com')
        sent_languages = []
        mock_send.side_effect = lambda *args, **kwargs: sent_languages.append(translation.get_language())

        # WHEN
        with userhelper.given_languages_supported('en', 'es'):
            response = self.client.post(reverse('auth_token_oauth'),
                                        json.dumps({'id_token': 'token', 'provider': 'google', 'language': 'es'}),
                                        content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_settings = UserSettings.objects.get(user__email='lang@gmail.com')
        self.assertEqual(user_settings.language, 'es')
        self.assertEqual(sent_languages, ['es'])

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_without_a_language_defaults_to_english(self, mock_verify_token):
        # GIVEN
        self._given_new_google_user(mock_verify_token, 'nolang@gmail.com')

        # WHEN
        response = self.client.post(reverse('auth_token_oauth'),
                                    json.dumps({'id_token': 'token', 'provider': 'google'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserSettings.objects.get(user__email='nolang@gmail.com').language, 'en')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_leaves_an_existing_users_language(self, mock_verify_token):
        # GIVEN
        user = userhelper.given_a_user_exists(email='existing@gmail.com')
        user.settings.language = 'de'
        user.settings.save()
        self._given_new_google_user(mock_verify_token, 'existing@gmail.com')

        # WHEN
        with userhelper.given_languages_supported('en', 'es'):
            response = self.client.post(reverse('auth_token_oauth'),
                                        json.dumps({'id_token': 'token', 'provider': 'google', 'language': 'es'}),
                                        content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.settings.refresh_from_db()
        self.assertEqual(user.settings.language, 'de')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_with_an_unsupported_language_fails(self, mock_verify_token):
        # GIVEN
        self._given_new_google_user(mock_verify_token, 'badlang@gmail.com')

        # WHEN
        response = self.client.post(reverse('auth_token_oauth'),
                                    json.dumps({'id_token': 'token', 'provider': 'google', 'language': 'xx'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('language', response.data)
        self.assertFalse(get_user_model().objects.filter(email='badlang@gmail.com').exists())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_of_an_existing_user_ignores_an_unsupported_language(self, mock_verify_token):
        # GIVEN
        user = userhelper.given_a_user_exists(email='existing@gmail.com')
        self._given_new_google_user(mock_verify_token, 'existing@gmail.com')

        # WHEN
        response = self.client.post(reverse('auth_token_oauth'),
                                    json.dumps({'id_token': 'token', 'provider': 'google', 'language': 'xx'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.settings.refresh_from_db()
        self.assertEqual(user.settings.language, 'en')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_saves_the_time_zone_of_a_new_user(self, mock_verify_token):
        # GIVEN
        self._given_new_google_user(mock_verify_token, 'zone@gmail.com')

        # WHEN
        response = self.client.post(reverse('auth_token_oauth'),
                                    json.dumps({'id_token': 'token', 'provider': 'google',
                                                'time_zone': 'Europe/Amsterdam'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserSettings.objects.get(user__email='zone@gmail.com').time_zone, 'Europe/Amsterdam')

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_with_an_unsupported_time_zone_fails(self, mock_verify_token):
        # GIVEN
        self._given_new_google_user(mock_verify_token, 'badzone@gmail.com')

        # WHEN
        response = self.client.post(reverse('auth_token_oauth'),
                                    json.dumps({'id_token': 'token', 'provider': 'google', 'time_zone': 'Mars/Base'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time_zone', response.data)
        self.assertFalse(get_user_model().objects.filter(email='badzone@gmail.com').exists())

    @patch('helium.auth.services.authservice.firebase_auth.verify_id_token')
    def test_oauth_login_of_an_existing_user_ignores_an_unsupported_time_zone(self, mock_verify_token):
        # GIVEN
        user = userhelper.given_a_user_exists(email='existingzone@gmail.com', time_zone='America/Chicago')
        self._given_new_google_user(mock_verify_token, 'existingzone@gmail.com')

        # WHEN
        response = self.client.post(reverse('auth_token_oauth'),
                                    json.dumps({'id_token': 'token', 'provider': 'google', 'time_zone': 'Mars/Base'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.settings.refresh_from_db()
        self.assertEqual(user.settings.time_zone, 'America/Chicago')
