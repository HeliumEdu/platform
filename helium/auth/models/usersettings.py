"""
UserSettings model.
"""

import logging

from builtins import str
from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class UserSettings(BaseModel):
    time_zone = models.CharField(default='America/Los_Angeles', max_length=255, choices=enums.TIME_ZONE_CHOICES)

    default_view = models.PositiveIntegerField(choices=enums.VIEW_CHOICES, default=enums.MONTH)

    week_starts_on = models.PositiveIntegerField(choices=enums.DAY_OF_WEEK_CHOICES, default=enums.SUNDAY)

    all_day_offset = models.PositiveIntegerField(default=30)

    show_getting_started = models.BooleanField(default=True)

    events_color = models.CharField(max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    default_reminder_offset = models.PositiveIntegerField(default=30)

    default_reminder_offset_type = models.PositiveIntegerField(default=enums.MINUTES,
                                                               choices=enums.REMINDER_OFFSET_TYPE_CHOICES)

    default_reminder_type = models.PositiveIntegerField(default=enums.POPUP, choices=enums.REMINDER_TYPE_CHOICES)

    receive_emails_from_admin = models.BooleanField(default=True)

    events_private_slug = models.SlugField(blank=True, null=True)

    private_slug = models.SlugField(blank=True, null=True)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='settings', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'User settings'

    def __str__(self):
        return '{} ({})'.format(self.pk, self.user.get_username())
