from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseGeneralViews(TestCase):
    def test_general_views(self):
        for url in ['home', 'terms', 'privacy', 'press', 'about', 'contact']:
            response = self.client.get(reverse(url))

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTemplateUsed(response, url + '.html')

        response = self.client.get(reverse('support'))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], settings.SUPPORT_REDIRECT_URL)
