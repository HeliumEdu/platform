import datetime
from unittest import mock

from django.conf import settings
from django.db import OperationalError
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.tasks import (
    email_reminders, push_reminders, process_email_reminder, process_push_reminder,
    recalculate_course_grade,
    recalculate_course_grades_for_course_group,
    recalculate_category_grades_for_course, adjust_reminder_times, send_email_reminder
)
from helium.planner.tests.helpers import (
    coursegrouphelper, coursehelper, categoryhelper, eventhelper, homeworkhelper, reminderhelper
)


class TestCasePlannerTasks(TestCase):
    def given_a_due_reminder(self, type):
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(
            user,
            start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
            end=timezone.now() + datetime.timedelta(minutes=10))
        return reminderhelper.given_reminder_exists(user, type=type, event=event)

    @mock.patch('helium.planner.tasks.taskutils.safe_apply_async')
    def test_email_reminders_queues_a_task_for_each_due_reminder(self, mock_apply):
        # GIVEN
        reminder = self.given_a_due_reminder(enums.EMAIL)

        # WHEN
        email_reminders()

        # THEN
        queued = [c.kwargs['args'][0] for c in mock_apply.call_args_list]
        self.assertEqual(queued, [reminder.pk])

    @mock.patch('helium.planner.tasks.taskutils.safe_apply_async')
    def test_push_reminders_queues_a_task_for_each_due_reminder(self, mock_apply):
        # GIVEN
        reminder = self.given_a_due_reminder(enums.PUSH)

        # WHEN
        push_reminders()

        # THEN
        queued = [c.kwargs['args'][0] for c in mock_apply.call_args_list]
        self.assertEqual(queued, [reminder.pk])

    @mock.patch('helium.planner.services.reminderservice.process_email_reminder')
    def test_process_email_reminder_delegates_to_the_service(self, mock_process):
        # WHEN
        process_email_reminder(7)

        # THEN
        mock_process.assert_called_once_with(7)

    @mock.patch('helium.planner.services.reminderservice.process_push_reminder')
    def test_process_push_reminder_delegates_to_the_service(self, mock_process):
        # WHEN
        process_push_reminder(7)

        # THEN
        mock_process.assert_called_once_with(7)

    @mock.patch('helium.planner.tasks.recalculate_course_grade')
    def test_recalculate_course_grades_for_course_group(self, mock_recalculate_course_grade):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        coursehelper.given_course_exists(course_group, title='Course 1')
        coursehelper.given_course_exists(course_group, title='Course 2')

        # WHEN
        recalculate_course_grades_for_course_group(course_group.pk)

        # THEN
        self.assertEqual(mock_recalculate_course_grade.call_count, 2)

    @mock.patch('helium.planner.tasks.recalculate_category_grade')
    def test_recalculate_category_grades_for_course(self, mock_recalculate_category_grade):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        categoryhelper.given_category_exists(course, title='Category 1')
        categoryhelper.given_category_exists(course, title='Category 2')

        # WHEN
        recalculate_category_grades_for_course(course.pk)

        # THEN
        self.assertEqual(mock_recalculate_category_grade.call_count, 2)

    @mock.patch('helium.planner.tasks.taskutils.safe_apply_async')
    @mock.patch('helium.planner.tasks.gradingservice.recalculate_course_grade')
    def test_recalculate_course_grade_retries_on_deadlock(self, mock_recalculate, mock_safe_apply_async):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        mock_recalculate.side_effect = OperationalError(
            1213, 'Deadlock found when trying to get lock; try restarting transaction')

        # WHEN
        recalculate_course_grade(course.pk)

        # THEN
        mock_safe_apply_async.assert_called_once()

    @mock.patch('helium.planner.tasks.taskutils.safe_apply_async')
    @mock.patch('helium.planner.tasks.gradingservice.recalculate_course_grade')
    def test_recalculate_course_grade_reraises_non_retryable_operational_error(self, mock_recalculate,
                                                                               mock_safe_apply_async):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        mock_recalculate.side_effect = OperationalError(2006, 'MySQL server has gone away')

        # WHEN
        with self.assertRaises(OperationalError):
            recalculate_course_grade(course.pk)

        # THEN
        mock_safe_apply_async.assert_not_called()

    @mock.patch('helium.planner.tasks.taskutils.safe_apply_async')
    @mock.patch('helium.planner.tasks.gradingservice.recalculate_course_grade')
    def test_recalculate_course_grade_raises_deadlock_after_exhausting_retries(self, mock_recalculate,
                                                                               mock_safe_apply_async):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        mock_recalculate.side_effect = OperationalError(
            1213, 'Deadlock found when trying to get lock; try restarting transaction')

        # WHEN
        with self.assertRaises(OperationalError):
            recalculate_course_grade(course.pk, retries=settings.DB_INTEGRITY_RETRIES)

        # THEN
        mock_safe_apply_async.assert_not_called()

    def test_adjust_reminder_times(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        original_start_of_range = reminder.start_of_range

        # Update event start time
        event.start = datetime.datetime(2017, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event.end = datetime.datetime(2017, 6, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event.save()

        # WHEN
        adjust_reminder_times(event.pk, enums.EVENT)

        # THEN
        reminder.refresh_from_db()
        # start_of_range should have been recalculated
        self.assertNotEqual(reminder.start_of_range, original_start_of_range)

    def test_adjust_reminder_times_for_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework)
        original_start_of_range = reminder.start_of_range

        # Update homework start time
        homework.start = datetime.datetime(2017, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        homework.end = datetime.datetime(2017, 6, 20, 12, 0, 0, tzinfo=datetime.timezone.utc)
        homework.save()

        # WHEN
        adjust_reminder_times(homework.pk, enums.HOMEWORK)

        # THEN
        reminder.refresh_from_db()
        self.assertNotEqual(reminder.start_of_range, original_start_of_range)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_for_event(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event)

        # WHEN
        send_email_reminder(user.email, 'Test Subject', reminder.pk, event.pk, enums.EVENT)

        # THEN
        mock_send_multipart_email.assert_called_once()

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_for_homework(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, homework=homework)

        # WHEN
        send_email_reminder(user.email, 'Test Subject', reminder.pk, homework.pk, enums.HOMEWORK)

        # THEN
        mock_send_multipart_email.assert_called_once()

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_nonexistent_reminder(self, mock_send_multipart_email):
        # WHEN
        send_email_reminder('test@email.com', 'Test Subject', 99999, 1, enums.EVENT)

        # THEN
        mock_send_multipart_email.assert_not_called()

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_nonexistent_event(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event)

        # WHEN
        send_email_reminder(user.email, 'Test Subject', reminder.pk, 99999, enums.EVENT)

        # THEN
        mock_send_multipart_email.assert_not_called()

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_nonexistent_homework(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, homework=homework)

        # WHEN
        send_email_reminder(user.email, 'Test Subject', reminder.pk, 99999, enums.HOMEWORK)

        # THEN
        mock_send_multipart_email.assert_not_called()

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_invalid_calendar_item_type(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event)

        # WHEN
        send_email_reminder(user.email, 'Test Subject', reminder.pk, event.pk, 'INVALID_TYPE')

        # THEN
        mock_send_multipart_email.assert_not_called()

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_send_email_reminder_with_empty_comments(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user, comments='   ')
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event)

        # WHEN
        send_email_reminder(user.email, 'Test Subject', reminder.pk, event.pk, enums.EVENT)

        # THEN
        mock_send_multipart_email.assert_called_once()
        # Verify comments is passed as None when empty
        call_args = mock_send_multipart_email.call_args
        self.assertIsNone(call_args[0][1]['comments'])
