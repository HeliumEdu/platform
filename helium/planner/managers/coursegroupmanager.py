__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from helium.common.managers.basemanager import BaseQuerySet, BaseManager

logger = logging.getLogger(__name__)


class CourseGroupQuerySet(BaseQuerySet):
    def exists_for_user(self, id, user_id):
        return self.filter(pk=id, user_id=user_id).exists()

    def for_user(self, user_id):
        return self.filter(user_id=user_id)


class CourseGroupManager(BaseManager):
    def get_queryset(self):
        return CourseGroupQuerySet(self.model, using=self._db)

    def exists_for_user(self, id, user_id):
        return self.get_queryset().exists_for_user(id, user_id)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)
