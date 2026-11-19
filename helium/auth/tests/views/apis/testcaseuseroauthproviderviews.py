import json
from unittest.mock import MagicMock, patch

from django.urls import reverse
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import UnavailableError
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.models import UserOAuthProvider
from helium.auth.tests.helpers import userhelper
from helium.common.tests.helpers import commonhelper


def given_firebase_links(*provider_ids):
    return MagicMock(provider_data=[MagicMock(provider_id=provider_id) for provider_id in provider_ids])


class TestCaseUserOAuthProviderViews(APITestCase):
    def setUp(self):
        self.mock_get_user = self.enterContext(patch('helium.auth.services.authservice.firebase_auth.get_user'))
        self.mock_update_user = self.enterContext(patch('helium.auth.services.authservice.firebase_auth.update_user'))
        self.mock_delete_user = self.enterContext(patch('helium.auth.services.authservice.firebase_auth.delete_user'))
        self.mock_verify_token = self.enterContext(
            patch('helium.auth.services.authservice.firebase_auth.verify_id_token'))

    def test_login_required(self):
        # WHEN
        responses = [
            self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'})),
            self.client.post(reverse('auth_user_oauthproviders_sync')),
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

    def test_remove_an_oauth_provider(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.set_unusable_password()
        user.save()
        UserOAuthProvider.objects.create(user=user, provider='google', provider_user_id='firebase-uid')
        UserOAuthProvider.objects.create(user=user, provider='microsoft', provider_user_id='firebase-uid')
        self.mock_get_user.return_value = given_firebase_links('google.com', 'microsoft.com')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.mock_update_user.assert_called_once_with('firebase-uid', providers_to_delete=['microsoft.com'])
        self.mock_delete_user.assert_not_called()
        self.assertEqual(['google'], list(user.oauth_providers.values_list('provider', flat=True)))

    def test_remove_the_last_firebase_provider_deletes_the_firebase_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        UserOAuthProvider.objects.create(user=user, provider='microsoft', provider_user_id='firebase-uid')
        self.mock_get_user.return_value = given_firebase_links('microsoft.com')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.mock_delete_user.assert_called_once_with('firebase-uid')
        self.mock_update_user.assert_not_called()
        self.assertFalse(user.oauth_providers.exists(),
                         'a Firebase user with no providers would keep the email and block signing in again')

    def test_remove_skips_the_firebase_unlink_for_a_provider_firebase_already_dropped(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        UserOAuthProvider.objects.create(user=user, provider='microsoft', provider_user_id='firebase-uid')
        self.mock_get_user.return_value = given_firebase_links('google.com')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.mock_update_user.assert_not_called()
        self.mock_delete_user.assert_not_called()
        self.assertFalse(user.oauth_providers.exists())

    def test_remove_an_oauth_provider_without_a_firebase_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        UserOAuthProvider.objects.create(user=user, provider='microsoft', provider_user_id='firebase-uid')
        self.mock_get_user.side_effect = firebase_auth.UserNotFoundError('No user record found')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(user.oauth_providers.exists())

    def test_remove_an_oauth_provider_firebase_failure_keeps_it(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        UserOAuthProvider.objects.create(user=user, provider='microsoft', provider_user_id='firebase-uid')
        self.mock_get_user.side_effect = UnavailableError('Firebase unavailable')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertTrue(user.oauth_providers.filter(provider='microsoft').exists())

    def test_removing_the_only_way_to_sign_in_is_refused(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.set_unusable_password()
        user.save()
        UserOAuthProvider.objects.create(user=user, provider='microsoft', provider_user_id='firebase-uid')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.mock_update_user.assert_not_called()
        self.assertTrue(user.oauth_providers.filter(provider='microsoft').exists())

    def test_removing_a_provider_not_linked_is_not_found(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        other_user = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        UserOAuthProvider.objects.create(user=user, provider='google', provider_user_id='firebase-uid')
        UserOAuthProvider.objects.create(user=other_user, provider='microsoft', provider_user_id='firebase-uid-2')

        # WHEN
        response = self.client.delete(reverse('auth_user_oauthproviders_detail', kwargs={'provider': 'microsoft'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(other_user.oauth_providers.filter(provider='microsoft').exists())

    def test_sync_links_a_provider_added_on_firebase(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        UserOAuthProvider.objects.create(user=user, provider='google', provider_user_id='firebase-uid')
        self.mock_verify_token.return_value = {'uid': 'firebase-uid'}
        self.mock_get_user.return_value = given_firebase_links('google.com', 'microsoft.com')

        # WHEN
        response = self.client.post(reverse('auth_user_oauthproviders_sync'),
                                    json.dumps({'id_token': 'valid-firebase-id-token'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(['google', 'microsoft'],
                         sorted(user.oauth_providers.values_list('provider', flat=True)))

    def test_sync_for_a_firebase_user_not_linked_is_refused(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        UserOAuthProvider.objects.create(user=user, provider='google', provider_user_id='firebase-uid')
        self.mock_verify_token.return_value = {'uid': 'someone-elses-uid'}

        # WHEN
        response = self.client.post(reverse('auth_user_oauthproviders_sync'),
                                    json.dumps({'id_token': 'valid-firebase-id-token'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_get_user.assert_not_called()

    def test_sync_with_an_invalid_token_is_refused(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        self.mock_verify_token.side_effect = firebase_auth.InvalidIdTokenError('Invalid token')

        # WHEN
        response = self.client.post(reverse('auth_user_oauthproviders_sync'),
                                    json.dumps({'id_token': 'bad-token'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, 'a 401 would sign the app out')
