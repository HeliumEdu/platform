from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from helium.auth.services.gettingstartedservice import is_getting_started_due
from helium.auth.tests.helpers import userhelper


class TestCaseGettingStartedService(TestCase):
    _users = 0

    def _given_import(self, imported_ago, last_shown_ago=None, show_getting_started=True):
        TestCaseGettingStartedService._users += 1
        name = f'user{TestCaseGettingStartedService._users}'
        user = userhelper.given_a_user_exists(username=name, email=f'{name}@example.com')
        now = timezone.now()
        get_user_model().objects.filter(pk=user.pk).update(example_schedule_imported_at=now - imported_ago)
        user.refresh_from_db()
        user.settings.show_getting_started = show_getting_started
        user.settings.getting_started_last_shown_at = None if last_shown_ago is None else now - last_shown_ago
        user.settings.save()
        return user.settings, now

    def test_not_due_once_the_example_schedule_is_gone(self):
        # GIVEN
        user_settings, now = self._given_import(timedelta(hours=1), show_getting_started=False)

        # WHEN
        due = is_getting_started_due(user_settings, now)

        # THEN
        self.assertFalse(due)

    def test_due_on_the_first_opportunity_after_import(self):
        # GIVEN
        user_settings, now = self._given_import(timedelta(minutes=5))

        # WHEN
        due = is_getting_started_due(user_settings, now)

        # THEN
        self.assertTrue(due)

    def test_first_week_shows_at_most_daily(self):
        # GIVEN
        recent, now = self._given_import(timedelta(days=2), last_shown_ago=timedelta(hours=19))
        stale, _ = self._given_import(timedelta(days=2), last_shown_ago=timedelta(hours=21))

        # WHEN
        recent_due = is_getting_started_due(recent, now)
        stale_due = is_getting_started_due(stale, now)

        # THEN
        self.assertFalse(recent_due)
        self.assertTrue(stale_due)

    def test_after_the_first_week_shows_at_most_weekly(self):
        # GIVEN
        recent, now = self._given_import(timedelta(days=9), last_shown_ago=timedelta(days=6))
        stale, _ = self._given_import(timedelta(days=9), last_shown_ago=timedelta(days=7, hours=1))

        # WHEN
        recent_due = is_getting_started_due(recent, now)
        stale_due = is_getting_started_due(stale, now)

        # THEN
        self.assertFalse(recent_due)
        self.assertTrue(stale_due)

    def test_never_due_once_the_import_reaches_the_adoption_age(self):
        # GIVEN
        user_settings, now = self._given_import(settings.EXAMPLE_SCHEDULE_ADOPTION_AGE)

        # WHEN
        due = is_getting_started_due(user_settings, now)

        # THEN
        self.assertFalse(due)

    def test_reimport_after_the_last_show_is_due_again(self):
        # GIVEN
        user_settings, now = self._given_import(timedelta(hours=1), last_shown_ago=timedelta(days=3))

        # WHEN
        due = is_getting_started_due(user_settings, now)

        # THEN
        self.assertTrue(due, 'A new import restarts the cadence')

    def test_without_an_import_stamp_shows_only_once(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        never_shown = user.settings
        now = timezone.now()

        # WHEN
        due_before = is_getting_started_due(never_shown, now)
        never_shown.getting_started_last_shown_at = now
        due_after = is_getting_started_due(never_shown, now + timedelta(days=1))

        # THEN
        self.assertTrue(due_before)
        self.assertFalse(due_after)
