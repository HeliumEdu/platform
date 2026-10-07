from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.importexport.tests.helpers import exampleschedulehelper
from helium.planner.models import CourseGroup, Course, Homework, Category, CourseSchedule, Event, Material, \
    MaterialGroup, Note


def _row_counts(user):
    return {model: model.objects.for_user(user.pk).count()
            for model in (CourseGroup, Course, Category, CourseSchedule, Homework, Event, MaterialGroup, Material,
                          Note)}


class TestCaseImportExampleSchedule(APITestCase):
    def setUp(self):
        self.enterContext(mock.patch('helium.auth.services.authservice.send_analytics_event.apply_async'))
        self.enterContext(mock.patch('helium.auth.services.authservice.metricutils.timing'))

    def _import(self):
        return self.client.post(reverse('importexport_import_exampleschedule'))

    def _clear(self):
        return self.client.delete(reverse('auth_user_resource_delete_exampleschedule'))

    def test_second_import_without_clearing_is_rejected_and_adds_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        self.assertEqual(self._import().status_code, status.HTTP_204_NO_CONTENT)
        counts_after_first_import = _row_counts(user)

        # WHEN
        response = self._import()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         ['The example schedule has already been imported. Please clear it before importing it '
                          'again.'])
        self.assertEqual(_row_counts(user), counts_after_first_import)

    def test_import_failure_releases_the_claim_so_the_import_can_be_retried(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)

        # WHEN
        with mock.patch('helium.importexport.views.apis.importviews.importservice.import_example_schedule',
                        side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self._import()

        # THEN
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.show_getting_started)
        self.assertEqual(self._import().status_code, status.HTTP_204_NO_CONTENT)

    def test_clear_right_after_import_deletes_everything(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        self.assertEqual(self._import().status_code, status.HTTP_204_NO_CONTENT)

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(sum(_row_counts(user).values()), 0)

    def test_clear_after_editing_the_imported_example_schedule_keeps_only_the_edited_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        self.assertEqual(self._import().status_code, status.HTTP_204_NO_CONTENT)
        homework = Homework.objects.for_user(user.pk).first()
        homework.title = 'Renamed by me'
        homework.save()
        kept_course_homework_count = Homework.objects.filter(course=homework.course).count()

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual([course.pk for course in Course.objects.for_user(user.pk)], [homework.course_id])
        self.assertEqual(Homework.objects.for_user(user.pk).count(), kept_course_homework_count)
        self.assertTrue(Homework.objects.filter(pk=homework.pk, title='Renamed by me').exists())
        self.assertEqual(Event.objects.for_user(user.pk).count(), 0)

    def test_reimport_after_a_partial_clear_leaves_the_kept_work_alone_and_isolates_the_new_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        example = exampleschedulehelper.given_example_schedule_exists(user)
        example.homework.title = 'Renamed by me'
        example.homework.save()
        self.assertEqual(self._clear().status_code, status.HTTP_400_BAD_REQUEST)
        kept_course_group = CourseGroup.objects.get(pk=example.course_group.pk)
        kept_updated_at = kept_course_group.updated_at
        kept_homework_updated_at = Homework.objects.get(pk=example.homework.pk).updated_at

        # WHEN
        reimport_response = self._import()

        # THEN
        self.assertEqual(reimport_response.status_code, status.HTTP_204_NO_CONTENT)
        new_course_group = CourseGroup.objects.exclude(pk=example.course_group.pk).get()
        self.assertTrue(new_course_group.example_schedule)
        self.assertFalse(CourseGroup.objects.get(pk=example.course_group.pk).example_schedule)
        self.assertEqual(CourseGroup.objects.get(pk=example.course_group.pk).updated_at, kept_updated_at)
        self.assertEqual(Homework.objects.get(pk=example.homework.pk).updated_at, kept_homework_updated_at)

        # WHEN
        second_clear_response = self._clear()

        # THEN
        self.assertEqual(second_clear_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CourseGroup.objects.filter(pk=new_course_group.pk).exists())
        self.assertTrue(CourseGroup.objects.filter(pk=example.course_group.pk).exists())
        self.assertTrue(Homework.objects.filter(pk=example.homework.pk, title='Renamed by me').exists())

    def test_reimport_promotes_an_edited_example_root_so_the_new_stamp_cannot_hide_the_edit(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        example = exampleschedulehelper.given_example_schedule_exists(user)
        example.homework.title = 'Renamed by me'
        example.homework.save()
        exampleschedulehelper.given_example_import_allowed(user)

        # WHEN
        self.assertEqual(self._import().status_code, status.HTTP_204_NO_CONTENT)

        # THEN
        self.assertFalse(CourseGroup.objects.get(pk=example.course_group.pk).example_schedule)
        user.refresh_from_db()
        self.assertGreater(user.example_schedule_imported_at, example.imported_at)

        # WHEN
        response = self._clear()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Homework.objects.filter(pk=example.homework.pk, title='Renamed by me').exists())
        self.assertTrue(CourseGroup.objects.filter(pk=example.course_group.pk).exists())
        self.assertFalse(Event.objects.filter(pk=example.event.pk).exists())
