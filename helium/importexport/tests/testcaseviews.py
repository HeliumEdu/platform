import logging

from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = "1.2.0"

logger = logging.getLogger(__name__)


class TestCaseImportExportViews(TestCase):
    def test_importexport_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('importexport_import')),
            self.client.post(reverse('importexport_export'))
        ]

        # THEN
        for response in responses:
            self.assertRedirects(response, reverse('login') + '?next={}'.format(response.request['PATH_INFO']))

    def test_import(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        # TODO: implement, note that this should parse from a file

        # THEN

    def test_export(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)
        # TODO: implement prepopulated data

        # WHEN
        # response = self.client.get(reverse('importexport_import'))

        # THEN
        # TODO: implement assertions
