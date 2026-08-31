import datetime
import logging

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

logger = logging.getLogger(__name__)


class ExternalCalendarQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(user_id=user_id)

    def needs_recached(self):
        start = timezone.now() - datetime.timedelta(seconds=settings.FEED_CACHE_REFRESH_TTL_SECONDS)
        return self.filter(Q(last_index__lte=start) |
                           Q(last_index__isnull=True)).filter(shown_on_calendar=True)


class ExternalCalendarManager(BaseManager):
    def get_queryset(self):
        return ExternalCalendarQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def needs_recached(self):
        return self.get_queryset().needs_recached()
