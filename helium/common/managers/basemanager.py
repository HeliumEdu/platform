import logging
from abc import abstractmethod

from django.db import models

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

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
