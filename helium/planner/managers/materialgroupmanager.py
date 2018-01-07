import logging

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class MaterialGroupQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()


class MaterialGroupManager(BaseManager):
    def get_queryset(self):
        return MaterialGroupQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)
