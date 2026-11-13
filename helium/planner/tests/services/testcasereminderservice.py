import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase
from kombu.exceptions import OperationalError
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Course, CourseSchedule, Reminder
from helium.planner.services import reminderservice
from helium.planner.tasks import adjust_reminder_times, email_reminders
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, homeworkhelper, eventhelper, reminderhelper


class TestCaseReminderService(TestCase):
    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                        end=timezone.now() + datetime.timedelta(minutes=10))
        event1 = eventhelper.given_event_exists(user,
                                                start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                end=timezone.now() + datetime.timedelta(minutes=10))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event1)
        reminder2 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, homework=homework)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, type=enums.EMAIL, sent=True, event=event1)

        # WHEN
        email_reminders()

        # THEN
        self.assertEqual(mock_send_multipart_email.call_count, 2)
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        reminder3.refresh_from_db()
        self.assertTrue(reminder1.sent)
        self.assertTrue(reminder2.sent)
        self.assertFalse(reminder3.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                        end=timezone.now() + datetime.timedelta(minutes=10))
        event1 = eventhelper.given_event_exists(user,
                                                start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                end=timezone.now() + datetime.timedelta(minutes=10))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, event=event1, type=enums.PUSH)
        reminder2 = reminderhelper.given_reminder_exists(user, homework=homework, type=enums.PUSH)
        # Course push reminder in the send window — should now be fully pushed (no guard)
        course_reminder = Reminder(
            message='Class soon',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([course_reminder])
        course_reminder = Reminder.objects.get(course=course, sent=False)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.PUSH, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, sent=True, event=event1)

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(mock_send_notifications.call_count, 3)
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        reminder3.refresh_from_db()
        course_reminder.refresh_from_db()
        self.assertTrue(reminder1.sent)
        self.assertTrue(reminder2.sent)
        self.assertFalse(reminder3.sent)
        self.assertTrue(course_reminder.sent)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders_inactive_user(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event)

        # WHEN
        email_reminders()

        # THEN
        # Inactive user should not receive email but reminder should be marked sent
        mock_send_multipart_email.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminder_renders_regional_time_format(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_format = enums.TWENTY_FOUR_HOUR
        user.settings.save()
        userhelper.given_user_push_token_exists(user)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, type=enums.PUSH)

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)

        # THEN
        mock_send_notifications.assert_called_once()
        self.assertEqual(mock_send_notifications.call_args[0][2], 'You need to do something now. · Mon, 05:00')

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminder_for_all_day_event_shows_only_the_weekday(self, mock_send_notifications):
        for zone_name in ('Asia/Tokyo', 'America/Chicago'):
            with self.subTest(zone=zone_name):
                # GIVEN
                mock_send_notifications.reset_mock()
                user = userhelper.given_a_user_exists(username=f'user_{zone_name}', email=f'{zone_name}@test.com',
                                                      time_zone=zone_name)
                userhelper.given_user_push_token_exists(user)
                local_midnight = datetime.datetime(2017, 5, 8, tzinfo=ZoneInfo(zone_name))
                event = eventhelper.given_event_exists(user, all_day=True, start=local_midnight,
                                                       end=local_midnight + datetime.timedelta(days=1))
                reminder = reminderhelper.given_reminder_exists(user, event=event, type=enums.PUSH)

                # WHEN
                reminderservice.process_push_reminder(reminder.pk)

                # THEN
                mock_send_notifications.assert_called_once()
                self.assertEqual(mock_send_notifications.call_args[0][2], 'You need to do something now. · Mon')

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_no_push_tokens(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        # No push tokens created for user
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.PUSH, event=event)

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        # No push sent when user has no push tokens
        mock_send_notifications.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_mark_sent_only(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.PUSH, event=event)

        # WHEN
        reminderservice.process_push_reminders(mark_sent_only=True)

        # THEN
        # No push sent when mark_sent_only=True, but reminder marked as sent
        mock_send_notifications.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    def test_heal_orphaned_repeating_reminders_creates_successor(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminder = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=True, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertTrue(Reminder.objects.filter(sent=False, course=course).exists())

    def test_heal_orphaned_repeating_reminders_skips_healthy_series(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        sent_reminder = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=True, dismissed=False,
            course=course, user=user,
        )
        unsent_reminder = Reminder(
            message='Test',
            start_of_range=timezone.now() + datetime.timedelta(days=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([sent_reminder, unsent_reminder])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)

    def test_heal_orphaned_repeating_reminders_heals_each_series_from_its_latest_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        courses = []
        for title in ('Course A', 'Course B'):
            course = coursehelper.given_course_exists(
                course_group,
                title=title,
                start_date=datetime.date.today() - datetime.timedelta(days=7),
                end_date=datetime.date.today() + datetime.timedelta(days=30)
            )
            courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                              mon_start_time=datetime.time(10, 0, 0),
                                                              wed_start_time=datetime.time(10, 0, 0),
                                                              fri_start_time=datetime.time(10, 0, 0))
            courses.append(course)
        orphaned = []
        for course in courses:
            for offset in (15, 30):
                orphaned.append(Reminder(
                    message=f'{course.title} {offset} older',
                    start_of_range=timezone.now() - datetime.timedelta(days=2),
                    offset=offset, offset_type=enums.MINUTES, type=enums.PUSH,
                    sent=True, dismissed=False, course=course, user=user,
                ))
                orphaned.append(Reminder(
                    message=f'{course.title} {offset} latest',
                    start_of_range=timezone.now() - datetime.timedelta(hours=2),
                    offset=offset, offset_type=enums.MINUTES, type=enums.PUSH,
                    sent=True, dismissed=False, course=course, user=user,
                ))
        healthy_unsent = Reminder(
            message='Healthy',
            start_of_range=timezone.now() + datetime.timedelta(days=2),
            offset=60, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, course=courses[0], user=user,
        )
        Reminder.objects.bulk_create(orphaned + [healthy_unsent])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        for course in courses:
            for offset in (15, 30):
                successors = Reminder.objects.filter(course=course, offset=offset, sent=False, dismissed=False)
                self.assertEqual(
                    list(successors.values_list('message', flat=True)), [f'{course.title} {offset} latest'])
        self.assertEqual(Reminder.objects.filter(course=courses[0], offset=60).count(), 1)
        self.assertEqual(Reminder.objects.count(), len(orphaned) + 1 + 4)

    def test_heal_orphaned_repeating_reminders_deletes_stale_and_creates_successor(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        stale = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=3),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, course=course, user=user,
        )
        Reminder.objects.bulk_create([stale])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual(Reminder.objects.filter(dismissed=False, sent=False).count(), 1)
        self.assertEqual(Reminder.objects.count(), 1)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders_course_creates_next(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        fired_reminder = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.EMAIL, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([fired_reminder])

        # WHEN
        email_reminders()

        # THEN
        self.assertEqual(Reminder.objects.filter(sent=True).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.count(), 2)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_auto_deletes_excess_past(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        old_past = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(days=2),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        pending = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([old_past, pending])

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(Reminder.objects.filter(sent=True, dismissed=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, dismissed=False, course=course).count(), 1)
        # The old_past record must be gone
        self.assertFalse(Reminder.objects.filter(pk=old_past.pk).exists())

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_auto_deletes_past_with_different_offset(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        old_past = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=2),
            offset=10, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        pending = Reminder(
            message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=9, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([old_past, pending])

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(Reminder.objects.filter(sent=True, dismissed=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, dismissed=False, course=course).count(), 1)
        self.assertFalse(Reminder.objects.filter(pk=old_past.pk).exists())

    def test_get_subject_orphaned_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        reminder.event = None
        reminder.homework = None
        reminder.course = None

        # WHEN
        subject = reminderservice.get_subject(reminder)

        # THEN
        self.assertIsNone(subject)

    def test_create_next_repeating_reminder_non_repeating(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)

    def test_create_next_repeating_reminder_no_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)

    def test_create_next_repeating_reminder_creates_next_occurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminder = reminderhelper.given_reminder_exists(user, course=course, type=enums.PUSH, sent=True,
                                                        start_of_range=timezone.now() - datetime.timedelta(hours=1))

        # WHEN
        new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNotNone(new_reminder)
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(new_reminder.course, course)
        self.assertEqual(new_reminder.user, user)
        self.assertEqual(new_reminder.type, enums.PUSH)
        self.assertTrue(new_reminder.repeating)
        self.assertFalse(new_reminder.sent)
        self.assertIsNotNone(new_reminder.start_of_range)
        # The new reminder must target a class strictly after the one that fired.
        offset_delta = datetime.timedelta(
            **{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
        fired_class_start = reminder.start_of_range + offset_delta
        new_class_start = new_reminder.start_of_range + offset_delta
        self.assertGreater(new_class_start, fired_class_start)

    @mock.patch('django.utils.timezone.now')
    def test_create_next_repeating_reminder_targets_next_class_not_current(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 30, 10, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='UTC')

        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2026, 3, 23),
            end_date=datetime.date(2026, 4, 30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        # Monday 2026-03-30 at 09:30 UTC: start_of_range of the fired reminder (class was at 10:00)
        monday_start_of_range = datetime.datetime(2026, 3, 30, 9, 30, 0, tzinfo=datetime.timezone.utc)
        reminder = Reminder(
            message='Test',
            start_of_range=monday_start_of_range,
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNotNone(new_reminder)
        expected_start_of_range = datetime.datetime(2026, 4, 1, 9, 30, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(new_reminder.start_of_range, expected_start_of_range)

    @mock.patch('django.utils.timezone.now')
    def test_create_next_repeating_reminder_uses_soonest_of_multiple_schedules_same_day(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 4, 8, 8, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='UTC')

        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2026, 3, 23),
            end_date=datetime.date(2026, 4, 30)
        )
        # `CourseSchedule.course` enforces unique=True, so a second schedule can't be persisted
        # for the same course — build it in memory and patch the queryset to simulate it.
        later_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0001000', wed_start_time=datetime.time(14, 0, 0))
        earlier_schedule = CourseSchedule(course=course, days_of_week='0001000',
                                          wed_start_time=datetime.time(9, 0, 0))

        # A reminder that fired just after midnight on Wednesday 2026-03-25, so both the 09:00
        # and 14:00 occurrences later that same day still qualify as "next".
        reminder = Reminder(
            message='Test',
            start_of_range=datetime.datetime(2026, 3, 24, 23, 30, 0, tzinfo=datetime.timezone.utc),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        with mock.patch.object(type(course.schedules), 'all', return_value=[later_schedule, earlier_schedule]):
            new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNotNone(new_reminder)
        expected_start_of_range = datetime.datetime(2026, 3, 25, 8, 30, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(new_reminder.start_of_range, expected_start_of_range)

    @mock.patch('django.utils.timezone.now')
    def test_get_next_course_occurrence_start_resolves_cycle_day(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 3, 8, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='UTC')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 31))
        courseschedulehelper.given_cycle_schedule_exists(
            course, cycle_length=2, anchor_date=datetime.date(2026, 3, 2),
            cycle_slots=[{'indices': [1], 'start_time': '09:00:00', 'end_time': '09:50:00'}])
        reminder = Reminder(course=course, user=user, offset=30, offset_type=enums.MINUTES, type=enums.PUSH)

        # WHEN
        next_start = reminder._get_next_course_occurrence_start()

        # THEN
        self.assertEqual(next_start, datetime.datetime(2026, 3, 4, 9, 0, 0, tzinfo=datetime.timezone.utc))

    @mock.patch('django.utils.timezone.now')
    def test_get_next_course_occurrence_start_skips_off_week_for_week_based(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 9, 8, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='UTC')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 31))
        courseschedulehelper.given_week_based_schedule_exists(
            course, days_of_week='0100000', week_offset=0, anchor_date=datetime.date(2026, 3, 2))
        reminder = Reminder(course=course, user=user, offset=30, offset_type=enums.MINUTES, type=enums.PUSH)

        # WHEN
        next_start = reminder._get_next_course_occurrence_start()

        # THEN
        self.assertEqual(next_start, datetime.datetime(2026, 3, 16, 9, 0, 0, tzinfo=datetime.timezone.utc))

    @mock.patch('django.utils.timezone.now')
    def test_get_next_course_occurrence_start_week_based_skips_exception_date(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 2, 7, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='UTC')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 31))
        course.exceptions = '20260302'
        course.save()
        courseschedulehelper.given_week_based_schedule_exists(
            course, days_of_week='0100000', week_offset=0, anchor_date=datetime.date(2026, 3, 2))
        reminder = Reminder(course=course, user=user, offset=30, offset_type=enums.MINUTES, type=enums.PUSH)

        # WHEN
        next_start = reminder._get_next_course_occurrence_start()

        # THEN
        self.assertEqual(next_start, datetime.datetime(2026, 3, 16, 9, 0, 0, tzinfo=datetime.timezone.utc))

    def test_create_next_repeating_reminder_no_future_occurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        # Course that has already ended
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2020, 1, 6),
            end_date=datetime.date(2020, 5, 8)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        # Manually build a reminder bypassing save() since the course has no future occurrence
        reminder = Reminder(
            message='Test',
            start_of_range=datetime.datetime(2020, 5, 4, 9, 30, tzinfo=datetime.timezone.utc),
            offset=30,
            offset_type=enums.MINUTES,
            type=enums.PUSH,
            course=course,
            user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)
        self.assertEqual(Reminder.objects.count(), 1)

    @mock.patch('django.utils.timezone.now')
    def test_get_next_course_occurrence_start_respects_schedule_window(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 2, 7, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='UTC')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 31))
        schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0100000',
            mon_start_time=datetime.time(9, 0, 0), mon_end_time=datetime.time(9, 50, 0))
        schedule.start_date = datetime.date(2026, 3, 9)
        schedule.save()
        reminder = Reminder(course=course, user=user, offset=30, offset_type=enums.MINUTES, type=enums.PUSH)

        # WHEN
        next_start = reminder._get_next_course_occurrence_start()

        # THEN
        self.assertEqual(next_start, datetime.datetime(2026, 3, 9, 9, 0, 0, tzinfo=datetime.timezone.utc))

    def test_clone_reminders_rejects_course_source(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN/THEN
        with self.assertRaises(ValueError):
            reminderservice.clone_reminders(course, homework)
        with self.assertRaises(ValueError):
            reminderservice.clone_reminders(homework, course)

    def test_heal_orphaned_repeating_reminders_leaves_non_course_reminders_alone(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        Reminder.objects.filter(pk=reminder.pk).update(
            start_of_range=timezone.now() - datetime.timedelta(
                minutes=settings.REMINDER_SEND_WINDOW_MINUTES + 60))

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertTrue(Reminder.objects.filter(pk=reminder.pk).exists())

    @mock.patch('django.utils.timezone.now')
    def test_heal_orphaned_repeating_reminders_skips_series_whose_course_ended_in_every_time_zone(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 9, 24, 6, 0, 0, tzinfo=datetime.timezone.utc)
        ahead = userhelper.given_a_user_exists(username='ahead', email='ahead@test.com',
                                               time_zone='Pacific/Auckland')
        behind = userhelper.given_a_user_exists(username='behind', email='behind@test.com',
                                                time_zone='Pacific/Honolulu')
        for user in (ahead, behind):
            course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user),
                                                      start_date=datetime.date(2026, 8, 24),
                                                      end_date=datetime.date(2026, 9, 22))
            reminderhelper.given_repeating_reminder_exists(
                user, course, datetime.datetime(2026, 9, 21, 20, 0, 0, tzinfo=datetime.timezone.utc), sent=True)

        # WHEN
        with mock.patch.object(reminderservice, 'create_next_repeating_reminder',
                               wraps=reminderservice.create_next_repeating_reminder) as mock_create:
            reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        mock_create.assert_not_called()

    @mock.patch('django.utils.timezone.now')
    def test_heal_orphaned_repeating_reminders_considers_series_whose_course_has_not_ended_everywhere(self,
                                                                                                    mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 9, 24, 6, 0, 0, tzinfo=datetime.timezone.utc)
        ahead = userhelper.given_a_user_exists(username='ahead', email='ahead@test.com',
                                               time_zone='Pacific/Auckland')
        behind = userhelper.given_a_user_exists(username='behind', email='behind@test.com',
                                                time_zone='Pacific/Honolulu')
        ended_locally = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(ahead),
                                                         start_date=datetime.date(2026, 8, 24),
                                                         end_date=datetime.date(2026, 9, 23))
        last_day_locally = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(behind),
                                                            start_date=datetime.date(2026, 8, 24),
                                                            end_date=datetime.date(2026, 9, 23))
        reminderhelper.given_repeating_reminder_exists(
            ahead, ended_locally, datetime.datetime(2026, 9, 22, 20, 0, 0, tzinfo=datetime.timezone.utc), sent=True)
        reminderhelper.given_repeating_reminder_exists(
            behind, last_day_locally, datetime.datetime(2026, 9, 23, 19, 30, 0, tzinfo=datetime.timezone.utc),
            sent=True)

        # WHEN
        with mock.patch.object(reminderservice, 'create_next_repeating_reminder',
                               wraps=reminderservice.create_next_repeating_reminder) as mock_create:
            reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual({call.args[0].course_id for call in mock_create.call_args_list},
                         {ended_locally.pk, last_day_locally.pk})

    @mock.patch('django.utils.timezone.now')
    def test_heal_orphaned_repeating_reminders_deletes_stale_reminder_on_ended_course(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 9, 24, 6, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists()
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user),
                                                  start_date=datetime.date(2026, 8, 24),
                                                  end_date=datetime.date(2026, 9, 18))
        reminderhelper.given_repeating_reminder_exists(
            user, course, datetime.datetime(2026, 9, 18, 14, 30, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertFalse(Reminder.objects.filter(course=course).exists())

    @mock.patch('django.utils.timezone.now')
    def test_heal_orphaned_repeating_reminders_resumes_series_when_course_end_date_is_extended(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 9, 24, 6, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists()
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user),
                                                  start_date=datetime.date(2026, 8, 24),
                                                  end_date=datetime.date(2026, 9, 18))
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminderhelper.given_repeating_reminder_exists(
            user, course, datetime.datetime(2026, 9, 18, 14, 30, 0, tzinfo=datetime.timezone.utc), sent=True)
        reminderservice.heal_orphaned_repeating_reminders()
        Course.objects.filter(pk=course.pk).update(end_date=datetime.date(2026, 10, 30))

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertTrue(Reminder.objects.filter(course=course, sent=False, dismissed=False).exists())

    @mock.patch('helium.planner.services.reminderservice.taskutils.safe_apply_async')
    def test_process_email_reminder_claims_before_a_concurrent_worker_can_send(self, mock_apply):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user, token='tok', device_id='phone')
        reminder = reminderhelper.given_due_reminder_exists(user, enums.EMAIL)
        concurrent_view = reminderservice._reminder_for_processing(reminder.pk)

        # WHEN
        reminderservice.process_email_reminder(reminder.pk)
        with mock.patch.object(reminderservice, '_reminder_for_processing',
                               return_value=concurrent_view):
            reminderservice.process_email_reminder(reminder.pk)

        # THEN
        self.assertEqual(mock_apply.call_count, 1)

    @mock.patch('helium.planner.services.reminderservice.taskutils.safe_apply_async')
    def test_process_push_reminder_claims_before_a_concurrent_worker_can_send(self, mock_apply):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user, token='tok', device_id='phone')
        reminder = reminderhelper.given_due_reminder_exists(user, enums.PUSH)
        userhelper.given_user_push_token_exists(reminder.user)
        concurrent_view = reminderservice._reminder_for_processing(reminder.pk, 'user__push_tokens')

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)
        with mock.patch.object(reminderservice, '_reminder_for_processing',
                               return_value=concurrent_view):
            reminderservice.process_push_reminder(reminder.pk)

        # THEN
        self.assertEqual(mock_apply.call_count, 1)

    def test_process_email_reminder_creates_only_one_successor_under_concurrency(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30))
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          mon_start_time=datetime.time(10, 0, 0))
        fired = Reminder(message='Test', start_of_range=timezone.now() - datetime.timedelta(minutes=1),
                         offset=15, offset_type=enums.MINUTES, type=enums.EMAIL,
                         sent=False, dismissed=False, course=course, user=user)
        Reminder.objects.bulk_create([fired])
        concurrent_view = reminderservice._reminder_for_processing(fired.pk)

        # WHEN
        reminderservice.process_email_reminder(fired.pk)
        with mock.patch.object(reminderservice, '_reminder_for_processing',
                               return_value=concurrent_view):
            reminderservice.process_email_reminder(fired.pk)

        # THEN
        self.assertEqual(Reminder.objects.filter(course=course, sent=False, dismissed=False).count(), 1)

    @mock.patch('helium.planner.services.reminderservice.send_pushes')
    def test_push_dispatch_failure_does_not_re_send_inline(self, mock_send_pushes):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user, token='tok', device_id='phone')
        reminder = reminderhelper.given_due_reminder_exists(user, enums.PUSH)
        mock_send_pushes.apply_async.side_effect = OperationalError('broker unavailable')

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)

        # THEN
        mock_send_pushes.apply_async.assert_called_once()
        mock_send_pushes.apply.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    @mock.patch('helium.planner.tasks.send_email_reminder')
    def test_email_dispatch_failure_does_not_re_send_inline(self, mock_send_email_reminder):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user, token='tok', device_id='phone')
        reminder = reminderhelper.given_due_reminder_exists(user, enums.EMAIL)
        mock_send_email_reminder.apply_async.side_effect = OperationalError('broker unavailable')

        # WHEN
        reminderservice.process_email_reminder(reminder.pk)

        # THEN
        mock_send_email_reminder.apply_async.assert_called_once()
        mock_send_email_reminder.apply.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    def test_firing_prunes_dismissed_past_occurrences(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)
        dismissed_past = reminderhelper.given_reminder_exists(
            user, course=course, type=enums.PUSH, offset=30, offset_type=enums.MINUTES,
            sent=True, dismissed=True,
            start_of_range=timezone.now() - datetime.timedelta(days=7))
        just_fired = reminderhelper.given_reminder_exists(
            user, course=course, type=enums.PUSH, offset=30, offset_type=enums.MINUTES,
            sent=True, start_of_range=timezone.now() - datetime.timedelta(minutes=1))

        # WHEN
        reminderservice._delete_excess_past_reminders(just_fired)

        # THEN
        self.assertFalse(Reminder.objects.filter(pk=dismissed_past.pk).exists())
        self.assertTrue(Reminder.objects.filter(pk=just_fired.pk).exists())


class TestCaseRecurringEventReminderService(TestCase):
    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_firing_arms_the_next_occurrence_and_keeps_one_past_record(self, mock_now, mock_send_notifications):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        userhelper.given_user_push_token_exists(user)
        event = eventhelper.given_weekly_event_exists(user)
        older = reminderhelper.given_reminder_exists(
            user, event=event, offset=30, sent=True,
            start_of_range=datetime.datetime(2030, 4, 29, 6, 30, tzinfo=datetime.timezone.utc))
        other_offset = reminderhelper.given_reminder_exists(
            user, event=event, offset=60, sent=True,
            start_of_range=datetime.datetime(2030, 4, 29, 6, 0, tzinfo=datetime.timezone.utc))
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=30)
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 35, tzinfo=datetime.timezone.utc)

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)

        # THEN
        mock_send_notifications.assert_called_once()
        self.assertEqual(mock_send_notifications.call_args[0][2], 'You need to do something now. · Mon, 9 AM')
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)
        self.assertFalse(Reminder.objects.filter(pk=older.pk).exists())
        self.assertTrue(Reminder.objects.filter(pk=other_offset.pk).exists())
        successor = Reminder.objects.get(event=event, offset=30, sent=False)
        self.assertEqual(successor.start_of_range, datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))
        self.assertEqual(successor.message, reminder.message)
        self.assertEqual(successor.type, enums.PUSH)

    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_firing_the_last_occurrence_queues_no_successor(self, mock_now, mock_send_notifications):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 4, 8, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        userhelper.given_user_push_token_exists(user)
        event = eventhelper.given_weekly_event_exists(user, recurrence_rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2')
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=30)
        mock_now.return_value = datetime.datetime(2030, 4, 8, 6, 35, tzinfo=datetime.timezone.utc)

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)

        # THEN
        mock_send_notifications.assert_called_once()
        self.assertEqual(list(Reminder.objects.filter(event=event).values_list('pk', 'sent')), [(reminder.pk, True)])

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    @mock.patch('django.utils.timezone.now')
    def test_email_shows_the_occurrence_time_rather_than_the_series_start(self, mock_now, mock_send_multipart_email):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 13, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=30, type=enums.EMAIL)
        mock_now.return_value = datetime.datetime(2030, 5, 13, 6, 35, tzinfo=datetime.timezone.utc)

        # WHEN
        reminderservice.process_email_reminder(reminder.pk)

        # THEN
        mock_send_multipart_email.assert_called_once()
        self.assertEqual(mock_send_multipart_email.call_args[0][1]['normalized_datetime'],
                         'Mon, May 13 at 9:00 AM to Mon, May 13 at 10:00 AM')

    @mock.patch('django.utils.timezone.now')
    def test_heal_rearms_a_series_whose_successor_is_missing(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user)
        fired = reminderhelper.given_reminder_exists(
            user, event=event, offset=30, sent=True,
            start_of_range=datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc))

        # WHEN
        reminderservice.heal_repeating_item_reminders()

        # THEN
        successor = Reminder.objects.get(event=event, sent=False)
        self.assertEqual(successor.start_of_range, datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))
        self.assertEqual(successor.offset, fired.offset)
        self.assertEqual(Reminder.objects.filter(event=event).count(), 2)

    @mock.patch('django.utils.timezone.now')
    def test_heal_leaves_an_armed_series_alone(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user)
        reminderhelper.given_reminder_exists(
            user, event=event, offset=30, sent=True,
            start_of_range=datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc))
        armed = reminderhelper.given_reminder_exists(user, event=event, offset=30)

        # WHEN
        reminderservice.heal_repeating_item_reminders()

        # THEN
        self.assertEqual(list(Reminder.objects.filter(event=event, sent=False).values_list('pk', flat=True)),
                         [armed.pk])
        self.assertEqual(Reminder.objects.filter(event=event).count(), 2)

    @mock.patch('django.utils.timezone.now')
    def test_heal_for_one_event_revives_a_series_older_than_the_periodic_lookback(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user)
        reminderhelper.given_reminder_exists(
            user, event=event, offset=30, sent=True,
            start_of_range=datetime.datetime(2028, 5, 1, 6, 30, tzinfo=datetime.timezone.utc))

        # WHEN
        reminderservice.heal_repeating_item_reminders()
        periodic_count = Reminder.objects.filter(event=event, sent=False).count()
        reminderservice.heal_repeating_item_reminders(event_id=event.pk)

        # THEN
        self.assertEqual(periodic_count, 0)
        self.assertEqual(Reminder.objects.get(event=event, sent=False).start_of_range,
                         datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))

    @mock.patch('django.utils.timezone.now')
    def test_adjust_reminder_times_rearms_a_series_after_its_rule_is_extended(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user, recurrence_rule='FREQ=WEEKLY;BYDAY=MO;COUNT=6')
        reminderhelper.given_reminder_exists(
            user, event=event, offset=30, sent=True,
            start_of_range=datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc))
        event.recurrence_rule = 'FREQ=WEEKLY;BYDAY=MO;COUNT=8'
        event.save()

        # WHEN
        adjust_reminder_times(event.pk, enums.EVENT)

        # THEN
        self.assertEqual(Reminder.objects.get(event=event, sent=False).start_of_range,
                         datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))

    @mock.patch('django.utils.timezone.now')
    def test_clone_reminders_from_a_recurring_event_copies_one_per_series(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        source = eventhelper.given_weekly_event_exists(user)
        reminderhelper.given_reminder_exists(
            user, event=source, offset=30, message='Old wording', sent=True,
            start_of_range=datetime.datetime(2030, 4, 29, 6, 30, tzinfo=datetime.timezone.utc))
        reminderhelper.given_reminder_exists(user, event=source, offset=30, message='Lecture soon')
        reminderhelper.given_reminder_exists(user, event=source, offset=1, offset_type=enums.DAYS,
                                             message='Lecture tomorrow')
        target_start = datetime.datetime(2030, 6, 1, 7, 0, tzinfo=datetime.timezone.utc)
        target = eventhelper.given_event_exists(user, start=target_start, end=target_start)

        # WHEN
        reminderservice.clone_reminders(source, target)

        # THEN
        self.assertEqual(sorted(target.reminders.values_list('message', 'offset', 'offset_type', 'sent')),
                         [('Lecture soon', 30, enums.MINUTES, False), ('Lecture tomorrow', 1, enums.DAYS, False)])

    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_heal_rearms_an_event_series_whose_reminder_missed_its_send_window(self, mock_now,
                                                                              mock_send_notifications):
        for index, zone in enumerate(('Europe/Amsterdam', 'America/Los_Angeles')):
            with self.subTest(zone=zone):
                # GIVEN
                mock_send_notifications.reset_mock()
                tz = ZoneInfo(zone)
                occurrence = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
                mock_now.return_value = occurrence - datetime.timedelta(hours=1)
                user = userhelper.given_a_user_exists(username=f'user{index}', email=f'user{index}@test.com',
                                                      time_zone=zone)
                userhelper.given_user_push_token_exists(user)
                event = eventhelper.given_weekly_event_exists(user)
                reminder = reminderhelper.given_reminder_exists(user, event=event, offset=15)
                mock_now.return_value = occurrence + datetime.timedelta(hours=1)

                # WHEN
                reminderservice.heal_orphaned_repeating_reminders()
                reminderservice.process_push_reminders()
                next_occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)
                mock_now.return_value = next_occurrence - datetime.timedelta(minutes=14)
                reminderservice.process_push_reminders()

                # THEN
                mock_send_notifications.assert_called_once()
                reminder.refresh_from_db()
                self.assertTrue(reminder.sent)
                self.assertEqual(reminder.start_of_range, next_occurrence - datetime.timedelta(minutes=15))


class TestCaseRecurringHomeworkReminderService(TestCase):
    @mock.patch('django.utils.timezone.now')
    def test_unsent_reminder_tracks_the_next_occurrence(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 4, 10, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        homework = coursehelper.given_weekly_homework_in_a_new_course_exists(user)

        # WHEN
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, offset=30)

        # THEN
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 4, 15, 6, 30, tzinfo=datetime.timezone.utc))

    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_firing_arms_one_successor_for_the_next_occurrence(self, mock_now, mock_send_notifications):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        userhelper.given_user_push_token_exists(user)
        homework = coursehelper.given_weekly_homework_in_a_new_course_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, offset=30)
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 35, tzinfo=datetime.timezone.utc)

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)

        # THEN
        mock_send_notifications.assert_called_once()
        self.assertTrue(Reminder.objects.get(pk=reminder.pk).sent)
        successor = Reminder.objects.get(homework=homework, sent=False)
        self.assertEqual(successor.start_of_range, datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))
        self.assertEqual(Reminder.objects.filter(homework=homework).count(), 2)

    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_push_shows_the_occurrence_it_fires_for_rather_than_the_series_start(self, mock_now,
                                                                                 mock_send_notifications):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 4, 1, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        userhelper.given_user_push_token_exists(user)
        start = datetime.datetime(2030, 4, 1, 7, 0, tzinfo=datetime.timezone.utc)
        homework = coursehelper.given_weekly_homework_in_a_new_course_exists(
            user, start=start, duration=datetime.timedelta(0), recurrence_rule='FREQ=WEEKLY;BYDAY=MO,WE;COUNT=4')
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, offset=30, type=enums.PUSH)
        mock_now.return_value = reminder.start_of_range + datetime.timedelta(minutes=1)

        # WHEN
        reminderservice.process_push_reminder(reminder.pk)

        # THEN
        mock_send_notifications.assert_called_once()
        self.assertTrue(mock_send_notifications.call_args[0][2].endswith(' · Wed, 9 AM'))

    @mock.patch('django.utils.timezone.now')
    def test_heal_rearms_a_homework_series_with_no_active_reminder(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 8, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        homework = coursehelper.given_weekly_homework_in_a_new_course_exists(user)
        reminderhelper.given_reminder_exists(
            user, homework=homework, offset=30, sent=True,
            start_of_range=datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc))

        # WHEN
        reminderservice.heal_repeating_item_reminders(homework_id=homework.pk)

        # THEN
        successor = Reminder.objects.get(homework=homework, sent=False)
        self.assertEqual(successor.start_of_range, datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))
        self.assertEqual(Reminder.objects.filter(homework=homework).count(), 2)

    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_heal_rearms_a_homework_series_whose_reminder_missed_its_send_window(self, mock_now,
                                                                              mock_send_notifications):
        for index, zone in enumerate(('Europe/Amsterdam', 'America/Los_Angeles')):
            with self.subTest(zone=zone):
                # GIVEN
                mock_send_notifications.reset_mock()
                tz = ZoneInfo(zone)
                occurrence = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
                mock_now.return_value = occurrence - datetime.timedelta(hours=1)
                user = userhelper.given_a_user_exists(username=f'user{index}', email=f'user{index}@test.com',
                                                      time_zone=zone)
                userhelper.given_user_push_token_exists(user)
                homework = coursehelper.given_weekly_homework_in_a_new_course_exists(user)
                reminder = reminderhelper.given_reminder_exists(user, homework=homework, offset=15)
                mock_now.return_value = occurrence + datetime.timedelta(hours=1)

                # WHEN
                reminderservice.heal_orphaned_repeating_reminders()
                reminderservice.process_push_reminders()
                next_occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)
                mock_now.return_value = next_occurrence - datetime.timedelta(minutes=14)
                reminderservice.process_push_reminders()

                # THEN
                mock_send_notifications.assert_called_once()
                reminder.refresh_from_db()
                self.assertTrue(reminder.sent)
                self.assertEqual(reminder.start_of_range, next_occurrence - datetime.timedelta(minutes=15))
