import datetime
from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.importexport.tests.helpers import exampleschedulehelper
from helium.planner.models import Attachment, Category, Course, CourseGroup, CourseSchedule, Event, Homework, \
    Material, MaterialGroup, Note, Reminder
from helium.planner.tests.helpers import attachmenthelper, categoryhelper, coursehelper, courseschedulehelper, \
    homeworkhelper, materialhelper, notehelper, reminderhelper

ALL_EXAMPLE_MODELS = (ExternalCalendar, CourseGroup, MaterialGroup, Event, Note, Course, CourseSchedule, Category,
                      Homework, Reminder, Material, Attachment)

COURSE_GROUP_TREE = ('course_group', 'course', 'schedule', 'category', 'homework', 'course_reminder',
                     'homework_reminder')

OTHER_COURSE_TREE = ('other_course', 'other_schedule', 'other_category', 'other_homework')



def _survivors(example, *names):
    return [getattr(example, name) for name in names]


def _set_and_save(instance, **fields):
    for name, value in fields.items():
        setattr(instance, name, value)
    instance.save()


class TestCaseUserExampleSchedule(APITestCase):
    def setUp(self):
        self.enterContext(mock.patch('helium.auth.services.authservice.send_analytics_event.apply_async'))
        self.enterContext(mock.patch('helium.auth.services.authservice.metricutils.timing'))

    def _given_a_user_with_an_example_schedule(self, **kwargs):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        example = exampleschedulehelper.given_example_schedule_exists(user, **kwargs)
        return user, example

    def _reset(self, user):
        for model in reversed(ALL_EXAMPLE_MODELS):
            model.objects.for_user(user.pk).delete()
        user.settings.show_getting_started = True
        user.settings.save()
        user.onboarding_completed_at = None
        user.save()

    def _clear(self):
        return self.client.delete(reverse('auth_user_resource_delete_exampleschedule'))

    def _row_count(self, user):
        return sum(model.objects.for_user(user.pk).count() for model in ALL_EXAMPLE_MODELS)

    def _assert_cleared_with_notice_keeping(self, response, user, example, survivors):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'The example schedule was cleared, except for anything that changed.'})
        user.refresh_from_db()
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.show_getting_started)
        self.assertIsNotNone(user.onboarding_completed_at)
        self.assertEqual(exampleschedulehelper.count_example_flagged(user), 0)
        for survivor in survivors:
            self.assertTrue(type(survivor).objects.filter(pk=survivor.pk).exists(),
                            msg=f'{type(survivor).__name__} {survivor.pk} was deleted')
        for untouched in _survivors(example, *OTHER_COURSE_TREE):
            self.assertFalse(type(untouched).objects.filter(pk=untouched.pk).exists(),
                             msg=f'untouched {type(untouched).__name__} {untouched.pk} was kept')

    def test_clear_untouched_example_schedule_deletes_everything(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self._row_count(user), 0)
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.show_getting_started)

    def test_clear_after_background_reminder_resave_still_deletes_everything(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()
        for reminder in Reminder.objects.for_user(user.pk):
            reminder.save(force_update=True)

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self._row_count(user), 0)

    def test_clear_after_user_adds_anything_beneath_an_example_root_keeps_that_root(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        additions = {
            'homework': (lambda e: homeworkhelper.given_homework_exists(e.course, title='My own assignment'),
                         'course_group'),
            'course': (lambda e: coursehelper.given_course_exists(e.course_group, title='My course'),
                       'course_group'),
            'schedule': (lambda e: courseschedulehelper.given_course_schedule_exists(e.course), 'course_group'),
            'category': (lambda e: categoryhelper.given_category_exists(e.course, title='My category'),
                         'course_group'),
            'homework attachment': (lambda e: attachmenthelper.given_attachment_exists(user, homework=e.homework),
                                    'course_group'),
            'course attachment': (lambda e: attachmenthelper.given_attachment_exists(user, course=e.course),
                                  'course_group'),
            'event attachment': (lambda e: attachmenthelper.given_attachment_exists(user, event=e.event), 'event'),
            'material': (lambda e: materialhelper.given_material_exists(e.material_group, title='My material'),
                         'material_group'),
        }

        for name, (add, root_name) in additions.items():
            with self.subTest(addition=name):
                example = exampleschedulehelper.given_example_schedule_exists(user)
                added = add(example)

                # WHEN
                response = self._clear()

                # THEN
                self._assert_cleared_with_notice_keeping(response, user, example,
                                                         [added, getattr(example, root_name)])

                self._reset(user)

    def test_clear_after_user_adds_reminders_still_deletes_everything(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()
        reminderhelper.given_reminder_exists(user, offset=45, homework=example.homework)
        reminderhelper.given_reminder_exists(user, offset=45, course=example.course)
        reminderhelper.given_reminder_exists(user, offset=45, event=example.event)

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(sum(model.objects.for_user(user.pk).count() for model in (CourseGroup, Event)), 0,
                         'Reminders never count as making the example schedule your own')

    def test_clear_after_user_edits_anything_in_an_example_schedule_keeps_what_was_edited(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        edits = {
            'homework': (lambda e: _set_and_save(e.homework, title='Mine'), list(COURSE_GROUP_TREE)),
            'course': (lambda e: _set_and_save(e.course, title='Mine'), list(COURSE_GROUP_TREE)),
            'course group': (lambda e: _set_and_save(e.course_group, title='Mine'), ['course_group']),
            'category': (lambda e: _set_and_save(e.category, title='Mine'), ['course_group', 'category']),
            'schedule': (lambda e: _set_and_save(e.schedule, mon_start_time=datetime.time(9, 0)),
                         ['course_group', 'schedule']),
            'event': (lambda e: _set_and_save(e.event, title='Mine'), ['event']),
            'material group': (lambda e: _set_and_save(e.material_group, title='Mine'),
                               ['material_group', 'material']),
            'material': (lambda e: _set_and_save(e.material, title='Mine'), ['material_group', 'material']),
            'note': (lambda e: _set_and_save(e.note, title='Mine'), ['note']),
            'external calendar': (lambda e: _set_and_save(e.external_calendar, title='Mine'),
                                  ['external_calendar']),
        }

        for name, (edit, survivor_names) in edits.items():
            with self.subTest(edit=name):
                example = exampleschedulehelper.given_example_schedule_exists(user)
                edit(example)

                # WHEN
                response = self._clear()

                # THEN
                self._assert_cleared_with_notice_keeping(response, user, example,
                                                         _survivors(example, *survivor_names))

                self._reset(user)

    def test_clear_after_user_edits_one_course_keeps_it_and_deletes_the_untouched_courses(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()
        _set_and_save(example.homework, title='Renamed by me')

        # WHEN
        response = self._clear()

        # THEN
        self._assert_cleared_with_notice_keeping(response, user, example, _survivors(example, *COURSE_GROUP_TREE))
        self.assertTrue(CourseGroup.objects.filter(pk=example.course_group.pk, example_schedule=False).exists())

    def test_clear_with_only_the_group_edited_keeps_the_empty_group_and_clears_the_rest(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()
        _set_and_save(example.course_group, title='Mine now')

        # WHEN
        response = self._clear()

        # THEN
        self._assert_cleared_with_notice_keeping(response, user, example, [example.course_group])
        self.assertTrue(CourseGroup.objects.filter(pk=example.course_group.pk, example_schedule=False).exists())
        self.assertEqual(Course.objects.filter(course_group=example.course_group).count(), 0)
        self.assertFalse(Note.objects.filter(pk=example.linked_note.pk).exists())
        self.assertFalse(Event.objects.filter(pk=example.event.pk).exists())
        self.assertFalse(MaterialGroup.objects.filter(pk=example.material_group.pk).exists())
        self.assertFalse(Material.objects.filter(pk=example.material.pk).exists())
        self.assertFalse(Note.objects.filter(pk=example.note.pk).exists())
        self.assertFalse(ExternalCalendar.objects.filter(pk=example.external_calendar.pk).exists())

        # WHEN
        rows_after_first_clear = self._row_count(user)
        second_response = self._clear()

        # THEN
        self.assertEqual(second_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self._row_count(user), rows_after_first_clear)

    def test_clear_with_edited_homework_unflags_the_example_note_linked_to_it(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()
        _set_and_save(example.homework, title='Renamed by me')

        # WHEN
        response = self._clear()

        # THEN
        self._assert_cleared_with_notice_keeping(response, user, example, [example.linked_note])
        self.assertFalse(Note.objects.get(pk=example.linked_note.pk).example_schedule)

    def test_clear_after_user_links_a_note_to_example_homework_keeps_the_group(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule()
        note = notehelper.given_note_linked_to_homework(user, example.homework, title='My study notes')

        # WHEN
        response = self._clear()

        # THEN
        self._assert_cleared_with_notice_keeping(response, user, example,
                                                 [note] + _survivors(example, *COURSE_GROUP_TREE))

    def test_clear_without_an_import_stamp_keeps_everything(self):
        # GIVEN
        user, example = self._given_a_user_with_an_example_schedule(stamped=False)

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'The example schedule was cleared, except for anything that changed.'})
        self.assertEqual(exampleschedulehelper.count_example_flagged(user), 0)
        for survivor in example.roots + [example.homework, example.other_homework]:
            self.assertTrue(type(survivor).objects.filter(pk=survivor.pk).exists(),
                            msg=f'{type(survivor).__name__} {survivor.pk} was deleted without an import stamp')
