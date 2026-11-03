import logging

from helium.common.managers.basemanager import BaseManager, BaseQuerySet

logger = logging.getLogger(__name__)


class ResourceQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, resource_group__user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(resource_group__user_id=user_id)

    def for_resource_group(self, resource_group_id):
        return self.filter(resource_group_id=resource_group_id)

    def with_courses(self, courses):
        return self.filter(courses__in=courses)


class ResourceManager(BaseManager):
    def get_queryset(self):
        return ResourceQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)

    def for_resource_group(self, resource_group_id):
        return self.get_queryset().for_resource_group(resource_group_id)

    def with_courses(self, courses):
        return self.get_queryset().with_courses(courses)
