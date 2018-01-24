import logging

from django.apps import apps

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, course_group__user_id=user_id).exists()

    def has_weighted_grading(self, id):
        Category = apps.get_model('planner', 'Category')

        return Category.objects.filter(course_id=id, weight__gt=0).exists()

    def for_user(self, user_id):
        return self.filter(course_group__user_id=user_id)

    def for_course_group(self, course_group_id):
        return self.filter(course_group_id=course_group_id)

    def graded(self):
        return self.filter(current_grade__gt=-1)


class CourseManager(BaseManager):
    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def has_weighted_grading(self, id):
        return self.get_queryset().has_weighted_grading(id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course_group(self, course_group_id):
        return self.get_queryset().for_course_group(course_group_id)

    def graded(self):
        return self.get_queryset().graded()