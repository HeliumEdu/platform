from datetime import timedelta

from django.db import router
from django.db.models.deletion import Collector
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.importexport.services import examplescheduleguardservice
from helium.importexport.services.examplescheduleguardservice import LEGACY_IMPORT_WINDOW
from helium.importexport.tests.helpers import exampleschedulehelper
from helium.planner.models import Attachment, Category, Course, CourseGroup, CourseSchedule, Event, Homework, \
    Material, MaterialGroup, Note, Reminder
from helium.planner.tests.helpers import attachmenthelper


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

    def test_legacy_edit_inside_the_window_is_pristine_and_outside_it_modifies_the_root(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        example = exampleschedulehelper.given_example_schedule_exists(user, stamped=False)
        created_at = CourseGroup.objects.get(pk=example.course_group.pk).created_at
        Homework.objects.filter(pk=example.homework.pk).update(updated_at=created_at + LEGACY_IMPORT_WINDOW - timedelta(seconds=1))

        # WHEN
        inside_window = examplescheduleguardservice.partition_example_schedule(user.pk)
        Homework.objects.filter(pk=example.homework.pk).update(updated_at=created_at + LEGACY_IMPORT_WINDOW + timedelta(seconds=1))
        outside_window = examplescheduleguardservice.partition_example_schedule(user.pk)

        # THEN
        self.assertEqual(inside_window.modified, [])
        self.assertEqual([root.pk for root in outside_window.modified], [example.course_group.pk])

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
