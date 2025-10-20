__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from django.db.models import Count

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

logger = logging.getLogger(__name__)


class CourseGroupQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(user_id=user_id)

    def num_courses(self):
        return self.aggregate(course_count=Count('courses'))['course_count']

    def num_homework(self):
        return self.aggregate(homework_count=Count('courses__homework'))['homework_count']

    def num_attachments(self):
        return self.aggregate(attachments_count=Count('courses__attachments'))['attachment_count']


class CourseGroupManager(BaseManager):
    def get_queryset(self):
        return CourseGroupQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def num_courses(self):
        return self.get_queryset().num_courses()

    def num_homework(self):
        return self.get_queryset().num_homework()

    def num_attachments(self):
        return self.get_queryset().num_attachments()
