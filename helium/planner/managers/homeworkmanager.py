import logging

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class HomeworkQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, course__course_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(course__course_group__user_id=user_id)

    def for_course(self, course_id):
        return self.filter(course_id=course_id)

    def for_course_group(self, course_group_id):
        return self.filter(course__course_group_id=course_group_id)

    def for_category(self, category_id):
        return self.filter(category_id=category_id)

    def graded(self):
        return self.filter(completed=True).exclude(current_grade='-1/100')


class HomeworkManager(BaseManager):
    def get_queryset(self):
        return HomeworkQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course_group(self, course_group_id):
        return self.get_queryset().for_course_group(course_group_id)

    def for_course(self, course_id):
        return self.get_queryset().for_course(course_id)

    def for_category(self, category_id):
        return self.get_queryset().for_category(category_id)

    def graded(self):
        return self.get_queryset().graded()
