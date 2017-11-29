"""
User model.
"""

import logging

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core import validators
from django.db import models
from django.utils import timezone

from helium.common.models.base import BaseModel
from helium.common.utils import generate_verification_code
from helium.users.managers.usermanager import UserManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    username = models.CharField(max_length=255, unique=True,
                                help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                                validators=[
                                    validators.RegexValidator(r'^[\w.@+-]+$',
                                                              'Enter a valid username, which means less than 30 characters consisting of letters, numbers, or these symbols: @+-_.',
                                                              'invalid'),
                                ],
                                error_messages={
                                    'unique': "A user with that username already exists.",
                                })

    email = models.EmailField(max_length=255, unique=True,
                              error_messages={
                                  'unique': "A user with that email already exists.",
                              })

    email_changing = models.EmailField(max_length=255, blank=True, null=True)

    is_staff = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)

    verification_code = models.SlugField(unique=True, default=generate_verification_code)

    date_joined = models.DateTimeField(default=timezone.now)

    # Manager
    objects = UserManager()

    # Fields required to define the abstracted Django user
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def get_full_name(self):
        """
        Retrieve the long name for the user.

        :return: The user's email address.
        """
        return self.email

    def get_short_name(self):
        """
        Retrieve the short name for the user.

        :return: The user's email address.
        """
        return self.email

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
