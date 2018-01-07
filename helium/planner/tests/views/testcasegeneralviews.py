from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseGeneralViews(TestCase):
    def test_login_required(self):
        for url in ['calendar', 'classes', 'materials', 'grades']:
            response = self.client.get(reverse(url))

            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertRedirects(response, reverse('login') + '?next={}'.format(reverse(url)))

    def test_general_views_authenticated(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        for url in ['calendar', 'classes', 'materials', 'grades']:
            response = self.client.get(reverse(url))

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTemplateUsed(response, url + '/main.html')
