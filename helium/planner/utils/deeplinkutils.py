# Paths are the app's routes (frontend `lib/config/app_router.dart`, checked by `test/config/app_router_test.dart`),
# the two should be kept in parity.

from django.conf import settings


def assignment_url(homework, step='details') -> str:
    """
    The deep link that opens ``homework`` in the app, at ``step`` ("details", "reminders" or "attachments").
    """
    return f'{settings.PROJECT_APP_HOST}/planner/assignment/{homework.pk}/{step}'


def event_url(event, step='details') -> str:
    """
    The deep link that opens ``event`` in the app, at ``step`` ("details", "reminders" or "attachments").
    """
    return f'{settings.PROJECT_APP_HOST}/planner/event/{event.pk}/{step}'


def class_url(course) -> str:
    """
    The deep link that opens ``course`` in the app.
    """
    return f'{settings.PROJECT_APP_HOST}/classes/{course.pk}/details'


def class_schedule_url(course) -> str:
    """
    The deep link that opens ``course``'s schedule in the app.
    """
    return f'{settings.PROJECT_APP_HOST}/classes/{course.pk}/schedule'


def note_url(note) -> str:
    """
    The deep link that opens ``note`` in the app.
    """
    return f'{settings.PROJECT_APP_HOST}/notebook/{note.pk}'
