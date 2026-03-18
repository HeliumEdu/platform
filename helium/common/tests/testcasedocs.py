__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status


class TestCaseDocs(TestCase):
    def test_docs(self):
        # GIVEN
        user = get_user_model().objects.create_user(username='admin', email='admin@test.com',
                                                    password='test_pass_1!')
        user.is_staff = True
        user.save()
        self.client.force_login(user)

        # WHEN
        response = self.client.get('/docs/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
