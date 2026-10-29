from django.contrib.auth import get_user_model
from django.urls import reverse
from knox.models import AuthToken
from oauth2_provider.models import get_access_token_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.services.tokenservice import blacklist_refresh_tokens, create_api_token, issue_session_tokens, \
    revoke_api_token, revoke_auth_tokens
from helium.auth.tests.helpers import oauthhelper, userhelper


class TestCaseTokenService(APITestCase):
    def test_issue_session_tokens(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        tokens = issue_session_tokens(user)

        # THEN
        self.assertEqual({'access', 'refresh'}, set(tokens))
        self.assertTrue(OutstandingToken.objects.filter(user=user, token=tokens['refresh']).exists())
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(status.HTTP_200_OK, self.client.get(reverse('auth_user_detail')).status_code)

    def test_blacklist_refresh_tokens_for_only_the_given_users(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        other_user = userhelper.given_a_user_exists(username='other_user', email='other@test.com')
        RefreshToken.for_user(user)
        RefreshToken.for_user(user).blacklist()
        RefreshToken.for_user(other_user)

        # WHEN
        blacklist_refresh_tokens([user])

        # THEN
        self.assertEqual(2, BlacklistedToken.objects.filter(token__user=user).count())
        self.assertEqual(0, BlacklistedToken.objects.filter(token__user=other_user).count())

    def test_blacklist_refresh_tokens_by_user_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        RefreshToken.for_user(user)

        # WHEN
        blacklist_refresh_tokens(get_user_model().objects.filter(pk=user.pk).values_list('pk', flat=True))

        # THEN
        self.assertEqual(1, BlacklistedToken.objects.filter(token__user=user).count())

    def test_create_api_token_replaces_the_existing_one(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        _, first = create_api_token(user)

        # WHEN
        instance, second = create_api_token(user)

        # THEN
        self.assertNotEqual(first, second)
        self.assertEqual([instance.pk], list(AuthToken.objects.filter(user=user).values_list('pk', flat=True)))

    def test_revoke_api_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        create_api_token(user)

        # WHEN
        revoke_api_token(user)

        # THEN
        self.assertFalse(AuthToken.objects.filter(user=user).exists())

    def test_revoke_auth_tokens(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        RefreshToken.for_user(user)
        create_api_token(user)

        # WHEN
        revoke_auth_tokens(user)

        # THEN
        self.assertEqual(1, BlacklistedToken.objects.filter(token__user=user).count())
        self.assertFalse(AuthToken.objects.filter(user=user).exists())

    def test_revoke_auth_tokens_revokes_oauth_grants(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        other_user = userhelper.given_a_user_exists(username='other_user', email='other@test.com')
        application = oauthhelper.given_oauth_application_exists()
        oauthhelper.given_oauth_token_exists(user, application)
        oauthhelper.given_oauth_token_exists(other_user, application, token='other-token')

        # WHEN
        revoke_auth_tokens(user)

        # THEN
        self.assertFalse(get_access_token_model().objects.filter(user=user).exists())
        self.assertTrue(get_access_token_model().objects.filter(user=other_user).exists())
