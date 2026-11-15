import importlib
from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper

migration = importlib.import_module('helium.auth.migrations.0080_user_example_schedule_first_imported_at')


class TestCaseBackfillExampleScheduleFirstImportedAt(TestCase):
    def test_starts_the_first_import_at_the_latest_one(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        imported_at = timezone.now() - timedelta(days=3)
        get_user_model().objects.filter(pk=user.pk).update(example_schedule_imported_at=imported_at,
                                                           example_schedule_first_imported_at=None)
        no_example_user = userhelper.given_a_user_exists(username='plain', email='plain@example.com')

        # WHEN
        migration.backfill_example_schedule_first_imported_at(apps, None)

        # THEN
        user.refresh_from_db()
        no_example_user.refresh_from_db()
        self.assertEqual(user.example_schedule_first_imported_at, imported_at)
        self.assertIsNone(no_example_user.example_schedule_first_imported_at)
