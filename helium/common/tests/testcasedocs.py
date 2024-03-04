__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from rest_framework import status
from rest_framework.test import APITestCase


class TestCaseDocs(APITestCase):
    def test_docs(self):
        # WHEN
        response = self.client.get('/docs/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
