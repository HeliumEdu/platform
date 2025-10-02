__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging
from abc import abstractmethod

from django.db import models

logger = logging.getLogger(__name__)


class BaseQuerySet(models.query.QuerySet):
    @abstractmethod
    def exists_for_user(self, id, user_id):
        """
        Checks whether or not the given instance exists for the given user.

        :param id: The unique ID of the instance for the current model.
        :param user_id: The ID of the user with which the instance should be associated.
        :return: True if the instance exists, False otherwise.
        """
        raise NotImplementedError


class BaseManager(models.Manager):
    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db)

    @abstractmethod
    def exists_for_user(self, id, user_id):
        """
        Checks whether or not the given instance exists for the given user.

        :param id: The unique ID of the instance for the current model.
        :param user_id: The ID of the user with which the instance should be associated.
        :return: True if the instance exists, False otherwise.
        """
        raise NotImplementedError
