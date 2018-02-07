import logging

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class ExternalCalendarQuerySet(BaseQuerySet):
    def for_user(self, user_id):
        return self.filter(user_id=user_id)


class ExternalCalendarManager(BaseManager):
    def get_queryset(self):
        return ExternalCalendarQuerySet(self.model, using=self._db)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)
