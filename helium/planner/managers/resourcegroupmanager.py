import logging

from django.db.models import Count

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

logger = logging.getLogger(__name__)


class ResourceGroupQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(user_id=user_id)

    def num_resources(self):
        return self.aggregate(resources_count=Count('resources'))['resources_count']


class ResourceGroupManager(BaseManager):
    def get_queryset(self):
        return ResourceGroupQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def num_resources(self):
        return self.get_queryset().num_resources()
