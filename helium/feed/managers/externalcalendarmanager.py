__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django.db.models import Q

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

logger = logging.getLogger(__name__)


class ExternalCalendarQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(user_id=user_id)

    def needs_recached(self, start):
        return self.filter(Q(last_index__lte=start) |
                           Q(last_index__isnull=True)).filter(shown_on_calendar=True)


class ExternalCalendarManager(BaseManager):
    def get_queryset(self):
        return ExternalCalendarQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def needs_recached(self, start):
        return self.get_queryset().needs_recached(start)
