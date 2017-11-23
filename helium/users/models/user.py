"""
User model.
"""

import logging

from helium.common import enums
from helium.common.models.base import BaseModel
from helium.users.managers.usermanager import UserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    first_name = models.CharField(max_length=30, blank=True)

    last_name = models.CharField(max_length=30, blank=True)

    email = models.EmailField(max_length=255, unique=True)

    is_staff = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    date_joined = models.DateTimeField(default=timezone.now)

    address_1 = models.CharField(max_length=255, blank=True, null=True)

    address_2 = models.CharField(max_length=255, blank=True, null=True)

    city = models.CharField(max_length=255, blank=True, null=True)

    state = models.CharField(choices=enums.STATE_CHOICES, max_length=2)

    postal_code = models.CharField(max_length=255, blank=True, null=True)

    country = models.CharField(max_length=255, blank=True, null=True, default='United States')

    phone = models.CharField(max_length=255, blank=True, null=True)

    time_zone = models.CharField(default='America/Chicago', max_length=255, choices=enums.TIME_ZONE_CHOICES)

    # Manager
    objects = UserManager()

    # Fields required to define the abstracted Django user
    USERNAME_FIELD = 'email'

    def get_full_name(self):
        """
        Retrieve the long name for the user.

        :return: The user's email address.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """
        Retrieve the short name for the user.

        :return: The user's email address.
        """
        return self.first_name

    def has_perm(self, perm, obj=None):
        """
        Check if this user has the given permission.

        :param perm: The permission to check for.
        :param obj: The object to check for permissions
        :return: True if the user has the permission, False otherwise.
        """
        return True

    def has_module_perms(self, app_label):
        """
        Check if the user has privileges to the given app

        :param app_label: The label of the app on which to check for permissions.
        :return: True if the user has privileges for app, False otherwise
        """
        return True

    def get_username(self):
        return getattr(self, self.USERNAME_FIELD)
