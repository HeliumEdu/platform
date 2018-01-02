from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseGeneralViews(TestCase):
    def test_general_views(self):
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        response = self.client.get(reverse('settings'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'settings/main.html')
