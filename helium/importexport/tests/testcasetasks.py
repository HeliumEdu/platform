__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.importexport.tasks import import_example_schedule


class TestCaseImportExportTasks(APITestCase):
    def test_import_example_schedule_sets_is_setup_complete(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        self.assertFalse(user.settings.is_setup_complete)

        # WHEN
        import_example_schedule(user.pk)

        # THEN
        user.refresh_from_db()
        self.assertTrue(user.settings.is_setup_complete)

    def test_import_example_schedule_nonexistent_user_does_not_fail(self):
        # GIVEN
        nonexistent_user_id = 99999

        # WHEN / THEN (should not raise)
        import_example_schedule(nonexistent_user_id)
