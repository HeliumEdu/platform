__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django.db import models
from django.db.models import Q
from django.utils import timezone

from helium.common import enums

logger = logging.getLogger(__name__)


class ReminderQuerySet(models.query.QuerySet):
    def for_user(self, user_id):
        return self.filter(user_id=user_id)

    def with_type(self, type):
        return self.filter(type=type)

    def unsent(self):
        return self.filter(sent=False)

    def for_today(self):
        today = timezone.now()
        return self.filter(start_of_range__lte=today).filter(Q(homework__isnull=False) | Q(event__isnull=False))

    def for_calendar_item(self, calendar_item_id, calendar_item_type):
        if calendar_item_type == enums.EVENT:
            return self.filter(event__pk=calendar_item_id)
        elif calendar_item_type == enums.HOMEWORK:
            return self.filter(homework__pk=calendar_item_id)
        else:
            return self.none()


class ReminderManager(models.Manager):
    def get_queryset(self):
        return ReminderQuerySet(self.model, using=self._db)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def with_type(self, type):
        return self.get_queryset().with_type(type)

    def unsent(self):
        return self.get_queryset().unsent()

    def for_today(self):
        return self.get_queryset().for_today()

    def for_calendar_item(self, calendar_item_id, calendar_item_type):
        return self.get_queryset().for_calendar_item(calendar_item_id, calendar_item_type)
