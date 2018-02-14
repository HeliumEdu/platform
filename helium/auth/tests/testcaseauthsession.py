from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.5'


class TestCaseAuthSession(APITestCase):
    def test_login_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('login') + '?next={}'.format(reverse('settings')),
                                    {'username': user.get_username(), 'password': 'test_pass_1!',
                                     'remember-me': 'remember-me'})

        # THEN
        self.assertRedirects(response, reverse('settings'))
        userhelper.verify_user_logged_in(self)

    def test_login_with_email_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('login'), {'username': user.email, 'password': 'test_pass_1!'})

        # THEN
        self.assertRedirects(response, reverse('planner'), fetch_redirect_response=False)
        userhelper.verify_user_logged_in(self)

    def test_logout_success(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        response = self.client.post(reverse('logout'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        userhelper.verify_user_not_logged_in(self)

    def test_login_invalid_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        responses = [
            self.client.post(reverse('login'), {'username': 'not-a-user', 'password': 'test_pass_1!'}),
            self.client.post(reverse('login'), {'username': user.get_username(), 'password': 'wrong_pass'})
        ]

        # THEN
        userhelper.verify_user_not_logged_in(self)
        for response in responses:
            self.assertContains(response, 'Check to make sure you entered your credentials properly',
                                status_code=status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_view_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists(self.client)

        # WHEN
        response1 = self.client.get(reverse('api_auth_user_detail'))
        self.client.login(username=user.get_username(), password='test_pass_1!')
        response2 = self.client.get(reverse('api_auth_user_detail'))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
