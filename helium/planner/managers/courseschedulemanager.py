__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

logger = logging.getLogger(__name__)


class CourseScheduleQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, course__course_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(course__course_group__user_id=user_id)

    def for_course(self, course_id):
        return self.filter(course_id=course_id)


class CourseScheduleManager(BaseManager):
    def get_queryset(self):
        return CourseScheduleQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        pass

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course(self, course_id):
        return self.get_queryset().for_course(course_id)
