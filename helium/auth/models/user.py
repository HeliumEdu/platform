import logging
import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.core import validators
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from helium.auth.managers.usermanager import UserManager
from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class User(AbstractBaseUser, BaseModel):
    username = models.CharField(help_text='A unique name used to login to the system.',
                                max_length=255, unique=True,
                                validators=[validators.RegexValidator(r'^[\w.@+-]+$',
                                                                      'Enter a valid username, which means less than '
                                                                      '30 characters consisting of letters, numbers, '
                                                                      'or these symbols: @+-_.',
                                                                      'invalid'), ],
                                error_messages={'unique': "Sorry, that username is already in use."})

    email = models.EmailField(help_text='A unique and valid email address.',
                              unique=True, error_messages={'unique': "Sorry, that email is already in use."})

    email_changing = models.EmailField(blank=True, null=True)

    is_active = models.BooleanField(default=False)

    verification_code = models.SlugField(
        help_text='The code sent to `email` when registering or changing an email address',
        default=uuid.uuid4, unique=True)

    is_superuser = models.BooleanField(default=False)

    # Manager
    objects = UserManager()

    # Fields required to define the abstracted Django user
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def get_user(self):
        return self

    def get_full_name(self):  # pragma: no cover
        """
        Retrieve the long name for the user.

        :return: The user's email address.
        """
        return self.email

    def get_short_name(self):  # pragma: no cover
        """
        Retrieve the short name for the user.

        :return: The user's email address.
        """
        return self.email

    def has_perm(self, perm, obj=None):  # pragma: no cover
        """
        Check if this user has the given permission.

        :param perm: The permission to check for.
        :param obj: The object to check for permissions
        :return: True if the user has the permission, False otherwise.
        """
        return True

    def has_module_perms(self, app_label):  # pragma: no cover
        """
        Check if the user has privileges to the given app

        :param app_label: The label of the app on which to check for permissions.
        :return: True if the user has privileges for app, False otherwise
        """
        return True

    @property
    def is_staff(self):
        """
        Check if this user has administrative privileges.

        :return: True if the user is an admin, False otherwise
        """
        return self.is_superuser


@receiver(post_save, sender=User)
def post_save_user(sender, instance, created, **kwargs):
    """
    After a user is created, one-to-one references to profile and settings models must be created to finish
    provisioning the new user.
    """
    if created:
        UserManager.create_references(instance)
