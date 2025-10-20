__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.13.15"

import logging

from django.db.models import Count

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

logger = logging.getLogger(__name__)


class MaterialGroupQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(user_id=user_id)

    def num_materials(self):
        return self.aggregate(materials_count=Count('materials'))['materials_count']


class MaterialGroupManager(BaseManager):
    def get_queryset(self):
        return MaterialGroupQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def num_materials(self):
        return self.get_queryset().num_materials()
