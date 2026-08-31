from django.test import TestCase
from rest_framework import status


class TestCaseDocs(TestCase):
    def test_docs_publicly_accessible(self):
        # GIVEN

        # WHEN
        response = self.client.get('/docs/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schema_publicly_accessible(self):
        # GIVEN

        # WHEN
        response = self.client.get('/schema/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
