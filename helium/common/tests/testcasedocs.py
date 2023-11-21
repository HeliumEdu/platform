import os

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Attachment
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, attachmenthelper, eventhelper, homeworkhelper

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Helium Edu"
__version__ = "1.4.51"


class TestCaseDocs(APITestCase):
    def test_docs(self):
        # WHEN
        response = self.client.get('/docs/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
