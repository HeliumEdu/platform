__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.test import TestCase

from helium.planner.handlers import signals
from helium.planner.models import Category, Course


class TestCaseSignals(TestCase):
    """Regression coverage for post_delete handlers firing during a cascade delete.

    When a CourseGroup (or Course) is deleted, Django's deletion collector can remove the
    parent row before the child's post_delete signal fires. The handler must schedule its
    grade recalculation from the instance's raw FK id rather than dereferencing the related
    object, which previously issued a DB fetch that raised and surfaced as a 500 on
    DELETE /planner/coursegroups/{pk}/. The recalculation task itself already no-ops on a
    missing parent.
    """

    def test_delete_category_tolerates_already_deleted_course(self):
        # GIVEN a Category whose parent Course row has already been removed mid-cascade
        instance = Category(pk=-1, course_id=-1)

        # WHEN the post_delete handler runs
        signals.delete_category(sender=Category, instance=instance)

        # THEN it does not raise (no DB fetch of the deleted Course; task no-ops)

    def test_delete_course_tolerates_already_deleted_course_group(self):
        # GIVEN a Course whose parent CourseGroup row has already been removed mid-cascade
        instance = Course(pk=-1, course_group_id=-1)

        # WHEN the post_delete handler runs
        signals.delete_course(sender=Course, instance=instance)

        # THEN it does not raise (no DB fetch of the deleted CourseGroup; task no-ops)
