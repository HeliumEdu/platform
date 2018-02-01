import logging

from django.db import models
from django.db.models import Q
from django.utils import timezone

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ReminderQuerySet(models.query.QuerySet):
    def with_type(self, type):
        return self.filter(type=type)

    def unsent(self):
        return self.filter(sent=False)

    def for_today(self):
        today = timezone.now()
        return self.filter(start_of_range__lte=today).filter(Q(homework__isnull=False) | Q(event__isnull=False))


class ReminderManager(models.Manager):
    def get_queryset(self):
        return ReminderQuerySet(self.model, using=self._db)

    def with_type(self, type):
        return self.get_queryset().with_type(type)

    def unsent(self):
        return self.get_queryset().unsent()

    def for_today(self):
        return self.get_queryset().for_today()
