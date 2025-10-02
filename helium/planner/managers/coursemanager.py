__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from django.apps import apps
from django.db.models import Count, Q, Case, When

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

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

    def num_homework(self):
        return self.aggregate(homework_count=Count('homework'))['homework_count']

    def num_homework_completed(self, completed=True):
        return self.aggregate(homework_count=Count(Case(When(homework__completed=completed, then=1))))['homework_count']

    def num_homework_graded(self):
        return self.aggregate(
            homework_count=Count(Case(
                When(Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'), then=1))))['homework_count']


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

    def num_homework(self):
        return self.get_queryset().num_homework()

    def num_homework_completed(self, completed=True):
        return self.get_queryset().num_homework_completed(completed)

    def num_homework_graded(self):
        return self.get_queryset().num_homework_graded()
