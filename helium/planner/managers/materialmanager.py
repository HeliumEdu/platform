import logging
from helium.common.managers.base import BaseManager, BaseQuerySet

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class MaterialQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, material_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(material_group__user_id=user_id)

    def for_material_group(self, material_group_id):
        return self.filter(material_group_id=material_group_id)


class MaterialManager(BaseManager):
    def get_queryset(self):
        return MaterialQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_material_group(self, material_group_id):
        return self.get_queryset().for_material_group(material_group_id)
