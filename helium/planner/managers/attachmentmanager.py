import logging

from django.db import models

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class AttachmentQuerySet(models.query.QuerySet):
    def for_course(self, course_id):
        return self.filter(course_id=course_id)

    def for_event(self, event_id):
        return self.filter(event_id=event_id)

    def for_homework(self, homework_id):
        return self.filter(homework_id=homework_id)


class AttachmentManager(models.Manager):
    def get_queryset(self):
        return AttachmentQuerySet(self.model, using=self._db)

    def for_course(self, course_id):
        return self.filter(course_id=course_id)

    def for_event(self, event_id):
        return self.filter(event_id=event_id)

    def for_homework(self, homework_id):
        return self.filter(homework_id=homework_id)
