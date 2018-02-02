import logging

from django.db.models import Count, Q, Case, When

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CategoryQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, course__course_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(course__course_group__user_id=user_id)

    def for_course(self, course_id):
        return self.filter(course_id=course_id)

    def num_homework_graded(self):
        return self.aggregate(
            homework_count=Count(Case(
                When(Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'), then=1))))['homework_count']


class CategoryManager(BaseManager):
    def get_uncategorized(self, course_id):
        return self.get_or_create(title='Uncategorized', course_id=course_id, defaults={'weight': 0})[0]

    def get_queryset(self):
        return CategoryQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_course(self, course_id):
        return self.get_queryset().for_course(course_id)

    def num_homework_graded(self):
        return self.get_queryset().num_homework_graded()
