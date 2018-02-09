import logging

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


class CourseScheduleQuerySet(BaseQuerySet):
    def for_user(self, user_id):
        return self.filter(course__course_group__user_id=user_id)

    def for_course(self, course_id):
        return self.filter(course_id=course_id)


class CourseScheduleManager(BaseManager):
    def get_queryset(self):
        return CourseScheduleQuerySet(self.model, using=self._db)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course(self, course_id):
        return self.get_queryset().for_course(course_id)
