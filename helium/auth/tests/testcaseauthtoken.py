from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.6'


class TestCaseAuthToken(APITestCase):
    def test_token_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        response = self.client.post(reverse('api_auth_token'),
                                    {'username': user.get_username(), 'password': 'test_pass_1!'})

        # THEN
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_token_with_email_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('api_auth_token'), {'username': user.email, 'password': 'test_pass_1!'})

        # THEN
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_revoke_token(self):
        # GIVEN
        userhelper.given_a_user_exists_and_token_set(self.client)

        # WHEN
        response1 = self.client.delete(reverse('api_auth_token_revoke'))
        response2 = self.client.get(reverse('api_auth_user_detail'))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Token.objects.count(), 0)

    def test_login_invalid_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        responses = [
            self.client.post(reverse('api_auth_token'), {'username': 'not-a-user', 'password': 'test_pass_1!'}),
            self.client.post(reverse('api_auth_token'), {'username': user.get_username(), 'password': 'wrong_pass'})
        ]

        # THEN
        userhelper.verify_user_not_logged_in(self)
        for response in responses:
            self.assertContains(response, 'provided credentials',
                                status_code=status.HTTP_400_BAD_REQUEST)

    def test_authenticated_view_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists(self.client)

        # WHEN
        response1 = self.client.get(reverse('api_auth_user_detail'))
        self.client.force_authenticate(user)
        response2 = self.client.get(reverse('api_auth_user_detail'))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
