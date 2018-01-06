import logging
from helium.common.managers.base import BaseQuerySet, BaseManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, course_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(course_group__user_id=user_id)

    def for_course_group(self, course_group_id):
        return self.filter(course_group_id=course_group_id)


class CourseManager(BaseManager):
    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course_group(self, course_group_id):
        return self.get_queryset().for_course_group(course_group_id)
