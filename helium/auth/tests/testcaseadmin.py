from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from helium.auth.admin import AdminUserPasswordChangeForm, force_logout
from helium.auth.models import UserPushToken
from helium.auth.tests.helpers import userhelper


class TestCaseAdmin(APITestCase):
    def test_force_logout_blacklists_sessions_but_keeps_api_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        self.client.post(reverse('auth_api_token'))
        userhelper.given_user_push_token_exists(user)
        admin_user = userhelper.given_a_user_exists(username='admin', email='admin@test.com')

        # WHEN
        force_logout(mock.Mock(), mock.Mock(user=admin_user), get_user_model().objects.filter(pk=user.pk))

        # THEN
        self.assertEqual(BlacklistedToken.objects.filter(token__user=user).count(), 1)
        self.assertEqual(UserPushToken.objects.filter(user=user).count(), 0)
        self.assertEqual(AuthToken.objects.filter(user=user).count(), 1)
        refresh = self.client.post(reverse('auth_token_refresh'), {'refresh': user.refresh}, format='json')
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_revokes_tokens(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        token = self.client.post(reverse('auth_api_token')).data['token']
        userhelper.given_user_push_token_exists(user)
        form = AdminUserPasswordChangeForm(user, data={'usable_password': 'true',
                                                       'password1': 'NewPass_Helium1!',
                                                       'password2': 'NewPass_Helium1!'})
        self.assertTrue(form.is_valid(), form.errors)

        # WHEN
        form.save()

        # THEN
        self.assertEqual(AuthToken.objects.filter(user=user).count(), 0)
        self.assertEqual(BlacklistedToken.objects.filter(token__user=user).count(), 1)
        self.assertEqual(UserPushToken.objects.filter(user=user).count(), 0)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code,
                         status.HTTP_401_UNAUTHORIZED)
