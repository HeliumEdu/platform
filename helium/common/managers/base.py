import logging
from abc import abstractmethod

from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.db.models import Q

from helium.auth.models.userprofile import UserProfile
from helium.auth.models.usersettings import UserSettings

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

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


class BaseManager(BaseUserManager):
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
