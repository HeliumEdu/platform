from datetime import timedelta

from django.conf import settings
from django.db import router
from django.db.models.deletion import Collector
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.importexport.services import examplescheduleguardservice
from helium.importexport.tests.helpers import exampleschedulehelper
from helium.planner.models import Attachment, Category, Course, CourseGroup, CourseSchedule, Event, Homework, \
    Material, MaterialGroup, Note, Reminder
from helium.planner.tests.helpers import attachmenthelper, reminderhelper


class TestCaseExampleScheduleGuardService(TestCase):
    def test_cascade_reaches_only_the_models_the_guard_was_reviewed_against(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        example = exampleschedulehelper.given_example_schedule_exists(user)
        attachmenthelper.given_attachment_exists(user, homework=example.homework)
        attachmenthelper.given_attachment_exists(user, event=example.event)

        # WHEN
        reached = set()
        for root in example.roots:
            collector = Collector(using=router.db_for_write(type(root)))
            collector.collect([root])
            reached.update(collector.data.keys())
            for queryset in collector.fast_deletes:
                reached.add(queryset.model)

        # THEN
        self.assertEqual({model for model in reached if not model._meta.auto_created},
                         {ExternalCalendar, CourseGroup, MaterialGroup, Event, Note, Course, CourseSchedule,
                          Category, Homework, Reminder, Material, Attachment})

    def test_unstamped_schedule_keeps_every_root(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        example = exampleschedulehelper.given_example_schedule_exists(user, stamped=False)

        # WHEN
        partition = examplescheduleguardservice.partition_example_schedule(user.pk)

        # THEN
        self.assertEqual(partition.pristine, [])
        self.assertEqual({type(root) for root in partition.modified}, {type(root) for root in example.roots})

    def test_reminder_activity_after_import_never_modifies_a_root(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        example = exampleschedulehelper.given_example_schedule_exists(user)
        example.course_reminder.sent = True
        example.course_reminder.save()
        reminderhelper.given_reminder_exists(user, course=example.course)
        reminderhelper.given_reminder_exists(user, homework=example.homework, message='My own reminder')
        example.homework_reminder.sent = True
        example.homework_reminder.dismissed = True
        example.homework_reminder.save()

        # WHEN
        partition = examplescheduleguardservice.partition_example_schedule(user.pk)

        # THEN
        self.assertEqual(partition.modified, [], 'Reminders fire, spawn successors and get dismissed on their own')

    def test_modified_group_keeps_the_edited_course_and_offers_the_untouched_course_for_deletion(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        example = exampleschedulehelper.given_example_schedule_exists(user)
        Homework.objects.filter(pk=example.homework.pk).update(updated_at=example.imported_at + timedelta(seconds=1))

        # WHEN
        partition = examplescheduleguardservice.partition_example_schedule(user.pk)

        # THEN
        self.assertEqual([root.pk for root in partition.modified], [example.course_group.pk])
        self.assertEqual([course.pk for course in partition.pristine_children], [example.other_course.pk])

    def test_adopt_unflags_every_example_entity_and_stops_the_dialog(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        exampleschedulehelper.given_example_schedule_exists(user)

        # WHEN
        examplescheduleguardservice.adopt(user.pk)

        # THEN
        user.settings.refresh_from_db()
        self.assertEqual(exampleschedulehelper.count_example_flagged(user), 0)
        self.assertFalse(user.settings.show_getting_started)
        self.assertEqual(Homework.objects.for_user(user.pk).count(), 2, 'Adoption never deletes')

    def test_adopt_stale_adopts_only_imports_older_than_the_adoption_age(self):
        # GIVEN
        stale_user = userhelper.given_a_user_exists(username='stale', email='stale@example.com')
        exampleschedulehelper.given_example_schedule_exists(stale_user, imported_ago=settings.EXAMPLE_SCHEDULE_ADOPTION_AGE + timedelta(hours=1))
        recent_user = userhelper.given_a_user_exists(username='recent', email='recent@example.com')
        exampleschedulehelper.given_example_schedule_exists(recent_user, imported_ago=settings.EXAMPLE_SCHEDULE_ADOPTION_AGE - timedelta(hours=1))
        recent_flagged = exampleschedulehelper.count_example_flagged(recent_user)

        # WHEN
        adopted = examplescheduleguardservice.adopt_stale()

        # THEN
        self.assertEqual(adopted, 1)
        self.assertEqual(exampleschedulehelper.count_example_flagged(stale_user), 0)
        self.assertEqual(exampleschedulehelper.count_example_flagged(recent_user), recent_flagged)

    def test_adopt_stale_skips_users_whose_example_schedule_is_already_gone(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        exampleschedulehelper.given_example_schedule_exists(user, imported_ago=settings.EXAMPLE_SCHEDULE_ADOPTION_AGE * 2)
        exampleschedulehelper.given_example_schedule_became_user_data(user)

        # WHEN
        adopted = examplescheduleguardservice.adopt_stale()

        # THEN
        self.assertEqual(adopted, 0)
