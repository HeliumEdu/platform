__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.14.1"

import logging

from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models import Q, Count

from helium.auth.models.userprofile import UserProfile
from helium.auth.models.usersettings import UserSettings
from helium.auth.utils.userutils import generate_verification_code

logger = logging.getLogger(__name__)


class UserQuerySet(models.query.QuerySet):
    def email_used(self, user_id, email):
        return self.filter(Q(email=email) | Q(email_changing=email)).exclude(pk=user_id).exists()

    def num_homework(self):
        return self.aggregate(homework_count=Count('course_group__courses__homework'))['homework_count']

    def num_events(self):
        return self.aggregate(events_count=Count('events'))['event_count']

    def num_attachments(self):
        return self.aggregate(attachments_count=Count('attachments'))['attachments_count']


class UserManager(BaseUserManager):
    @staticmethod
    def create_references(user):
        """
        Create necessary one-to-one references to profile and settings models for a user.

        :param user: the user to create the dependencies for
        """
        UserProfile.objects.create(user=user)
        UserSettings.objects.create(user=user)

    def create_user(self, username, email, password=None):  # pragma: no cover
        """
        Create a new user with the given username, password, and email.

        :param username: the username for the user
        :param email: the email for the new user
        :param password: the password for the new user
        :return: the created object
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            username=username
        )

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, username, password):  # pragma: no cover
        """
        Create a new super user with admin privileges.

        :param username: the username for the user
        :param email: the email for the new user
        :param password: the password for the new user
        :return: the created object
        """
        user = self.create_user(username=username,
                                email=email,
                                password=password)
        user.is_active = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        """
        Get the user for authentication/login from the database.

        :param username: the username to lookup
        :return: the user
        """
        return self.get(Q(username__iexact=username) | Q(email__iexact=username))

    def get_by_private_slug(self, private_slug):
        return self.get(settings__private_slug=private_slug)

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def email_used(self, user_id, email):
        return self.get_queryset().email_used(user_id, email)

    def num_homework(self):
        return self.get_queryset().num_homework()

    def num_events(self):
        return self.get_queryset().num_events()

    def num_attachments(self):
        return self.get_queryset().num_attachments()