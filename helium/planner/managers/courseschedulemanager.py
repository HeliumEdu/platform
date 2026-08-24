import logging

from django.db.models import Q

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

logger = logging.getLogger(__name__)


class CourseScheduleQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, course__course_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(course__course_group__user_id=user_id)

    def for_course(self, course_id):
        return self.filter(course_id=course_id)

    def rotating(self):
        return self.filter(Q(cycle_length__isnull=False) | Q(is_week_based=True))

    def meeting(self):
        """A cycle draws its times from `cycle_slots` and ignores `days_of_week`; weekly and
        week-based rows both fall through to the weekday match."""
        return self.filter(Q(cycle_length__isnull=False) | ~Q(days_of_week='0000000'))


class CourseScheduleManager(BaseManager):
    def get_queryset(self):
        return CourseScheduleQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course(self, course_id):
        return self.get_queryset().for_course(course_id)

    def rotating(self):
        return self.get_queryset().rotating()

    def meeting(self):
        return self.get_queryset().meeting()
