__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.db import models

logger = logging.getLogger(__name__)


class AttachmentQuerySet(models.query.QuerySet):
    def for_user(self, user_id):
        return self.filter(user_id=user_id)


class AttachmentManager(models.Manager):
    def get_queryset(self):
        return AttachmentQuerySet(self.model, using=self._db)

    def for_user(self, user_id):
        return self.get_queryset().for_user(user_id)
