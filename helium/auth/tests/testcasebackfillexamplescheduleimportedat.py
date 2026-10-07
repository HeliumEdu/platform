import importlib
from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup, Event
from helium.planner.tests.helpers import coursegrouphelper, eventhelper

migration = importlib.import_module('helium.auth.migrations.0077_backfill_example_schedule_imported_at')


class TestCaseBackfillExampleScheduleImportedAt(TestCase):
    def test_stamps_unstamped_users_with_example_data_from_their_earliest_example_root(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        coursegrouphelper.given_course_group_exists(user)
        eventhelper.given_event_exists(user)
        earliest = timezone.now() - timedelta(days=3)
        CourseGroup.objects.filter(user=user).update(example_schedule=True, created_at=earliest)
        Event.objects.filter(user=user).update(example_schedule=True, created_at=earliest + timedelta(hours=1))
        no_example_user = userhelper.given_a_user_exists(username='plain', email='plain@example.com')

        # WHEN
        migration.backfill_example_schedule_imported_at(apps, None)

        # THEN
        user.refresh_from_db()
        no_example_user.refresh_from_db()
        self.assertEqual(user.example_schedule_imported_at, earliest + migration.LEGACY_IMPORT_WINDOW)
        self.assertIsNone(no_example_user.example_schedule_imported_at)

    def test_leaves_existing_stamps_alone(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        coursegrouphelper.given_course_group_exists(user)
        CourseGroup.objects.filter(user=user).update(example_schedule=True)
        stamp = timezone.now() - timedelta(days=1)
        get_user_model().objects.filter(pk=user.pk).update(example_schedule_imported_at=stamp)

        # WHEN
        migration.backfill_example_schedule_imported_at(apps, None)

        # THEN
        user.refresh_from_db()
        self.assertEqual(user.example_schedule_imported_at, stamp)
