from datetime import datetime

from django.conf import settings
from django.utils import timezone


def is_getting_started_due(user_settings, now: datetime = None) -> bool:
    """
    Whether the "Getting Started" dialog should be shown now.

    It shows while the example schedule is still there: on the first opportunity after each import, then at most
    once per GETTING_STARTED_DAILY_GAP during the first GETTING_STARTED_DAILY_WINDOW, then at most once per
    GETTING_STARTED_WEEKLY_GAP, and never once the import is older than EXAMPLE_SCHEDULE_ADOPTION_AGE.

    :param user_settings: The user's settings.
    :param now: The current time, for tests.
    :return: True if the dialog should be shown now.
    """
    if not user_settings.show_getting_started:
        return False

    now = now or timezone.now()
    imported_at = user_settings.user.example_schedule_imported_at
    last_shown_at = user_settings.getting_started_last_shown_at

    if imported_at is None:
        return last_shown_at is None

    age = now - imported_at
    if age >= settings.EXAMPLE_SCHEDULE_ADOPTION_AGE:
        return False

    if last_shown_at is None or last_shown_at < imported_at:
        return True

    gap = (settings.GETTING_STARTED_DAILY_GAP if age < settings.GETTING_STARTED_DAILY_WINDOW
           else settings.GETTING_STARTED_WEEKLY_GAP)

    return now - last_shown_at >= gap
