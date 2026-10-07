from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.utils import timezone

from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.planner.models import Attachment, Category, Course, CourseGroup, CourseSchedule, Event, Homework, \
    Material, MaterialGroup, Note, Reminder
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, coursehelper, courseschedulehelper, \
    eventhelper, homeworkhelper, materialgrouphelper, materialhelper, notehelper, reminderhelper

_USER_OWNED_MODELS = (ExternalCalendar, CourseGroup, MaterialGroup, Event, Note, Course, CourseSchedule, Category,
                      Homework, Reminder, Material, Attachment)


def given_example_schedule_exists(user, stamped=True, imported_ago=timedelta(days=7)):
    """
    Build every kind of example schedule root with children, as if imported ``imported_ago`` ago, then stamp the
    user as the import does (or leave them unstamped, as for a schedule imported before stamping existed).
    """
    course_group = coursegrouphelper.given_course_group_exists(user)
    course = coursehelper.given_course_exists(course_group)
    schedule = courseschedulehelper.given_course_schedule_exists(course)
    category = categoryhelper.given_category_exists(course)
    homework = homeworkhelper.given_homework_exists(course, category=category)
    course_reminder = reminderhelper.given_reminder_exists(user, course=course)
    other_course = coursehelper.given_course_exists(course_group, title='🧪 Other Course')
    other_schedule = courseschedulehelper.given_course_schedule_exists(other_course)
    other_category = categoryhelper.given_category_exists(other_course, title='📊 Other Category')
    other_homework = homeworkhelper.given_homework_exists(other_course, title='💻 Other Homework',
                                                          category=other_category)
    homework_reminder = reminderhelper.given_reminder_exists(user, homework=homework)
    event = eventhelper.given_event_exists(user)
    material_group = materialgrouphelper.given_material_group_exists(user)
    material = materialhelper.given_material_exists(material_group)
    note = notehelper.given_note_exists(user)
    linked_note = notehelper.given_note_linked_to_homework(user, homework)
    external_calendar = externalcalendarhelper.given_external_calendar_exists(user)

    roots = [course_group, event, material_group, note, external_calendar]
    for flagged in roots + [linked_note]:
        flagged.example_schedule = True
        flagged.save()

    imported_at = timezone.now() - imported_ago
    for model in _USER_OWNED_MODELS:
        model.objects.for_user(user.pk).update(created_at=imported_at, updated_at=imported_at)

    get_user_model().objects.filter(pk=user.pk).update(example_schedule_imported_at=imported_at if stamped else None)
    user.refresh_from_db()

    return SimpleNamespace(course_group=course_group, course=course, schedule=schedule, category=category,
                           homework=homework, other_course=other_course, other_schedule=other_schedule,
                           other_category=other_category, other_homework=other_homework, course_reminder=course_reminder, homework_reminder=homework_reminder,
                           event=event, material_group=material_group, material=material, note=note,
                           linked_note=linked_note, external_calendar=external_calendar, roots=roots,
                           imported_at=imported_at)


def count_example_flagged(user):
    return sum(model.objects.for_user(user.pk).filter(example_schedule=True).count()
               for model in (ExternalCalendar, CourseGroup, MaterialGroup, Event, Note))


def given_example_import_allowed(user):
    user.settings.show_getting_started = False
    user.settings.save()


def given_example_schedule_became_user_data(user):
    for model in (ExternalCalendar, CourseGroup, MaterialGroup, Event, Note):
        model.objects.for_user(user.pk).update(example_schedule=False)
    given_example_import_allowed(user)
