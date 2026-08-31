from unittest import mock

from django.test import TestCase

from helium.planner.handlers import signals
from helium.planner.models import Category, Course, Homework


class TestCaseSignals(TestCase):
    def test_delete_category_tolerates_already_deleted_course(self):
        # GIVEN
        instance = Category(pk=-1, course_id=-1)

        # WHEN
        signals.delete_category(sender=Category, instance=instance)

        # THEN

    def test_delete_homework_tolerates_already_deleted_course(self):
        # GIVEN
        instance = Homework(pk=-1, course_id=-1)

        # WHEN
        with mock.patch.object(signals.logger, 'warning') as mock_warning:
            signals.delete_homework(sender=Homework, instance=instance)

        # THEN
        mock_warning.assert_not_called()

    def test_delete_course_tolerates_already_deleted_course_group(self):
        # GIVEN
        instance = Course(pk=-1, course_group_id=-1)

        # WHEN
        signals.delete_course(sender=Course, instance=instance)

        # THEN
