__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging
import time

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from helium.common import enums
from helium.common.models import BaseModel

logger = logging.getLogger(__name__)


class UserSettings(BaseModel):
    time_zone = models.CharField(help_text='A valid time zone choice.',
                                 default='America/Los_Angeles', max_length=255, choices=enums.TIME_ZONE_CHOICES)

    default_view = models.PositiveIntegerField(help_text='A valid default calendar view choice.',
                                               choices=enums.VIEW_CHOICES, default=enums.MONTH)

    week_starts_on = models.PositiveIntegerField(help_text='A valid day on which the week should start choice.',
                                                 choices=enums.DAY_OF_WEEK_CHOICES, default=enums.SUNDAY)

    all_day_offset = models.PositiveIntegerField(default=30)

    show_getting_started = models.BooleanField(help_text='Whether or not the "Getting Started" dialog should be shown.',
                                               default=True)

    events_color = models.CharField(
        help_text='A valid hex color code choice to determine the color events will be shown on the calendar',
        max_length=7, choices=enums.ALLOWED_COLORS, default='#ffad46')

    default_reminder_offset = models.PositiveIntegerField(help_text='The default offset when creating a new reminder.',
                                                          default=30)

    default_reminder_offset_type = models.PositiveIntegerField(
        help_text='A valid default type of time offset choice when creating a new reminder.',
        default=enums.MINUTES,
        choices=enums.REMINDER_OFFSET_TYPE_CHOICES)

    default_reminder_type = models.PositiveIntegerField(
        help_text='A valid default type of reminder choice when creating a new reminder.',
        default=enums.POPUP, choices=enums.REMINDER_TYPE_CHOICES)

    receive_emails_from_admin = models.BooleanField(
        help_text='Whether or not the `email` on file should receive bulletin emails.',
        default=True)

    private_slug = models.SlugField(blank=True, null=True)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='settings', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'User settings'

    def __str__(self):  # pragma: no cover
        return f'{self.pk} ({self.user.get_username()})'

    def get_user(self):
        return self.user

    def enable_private_slug(self):
        if not self.private_slug:
            self.private_slug = slugify(str(self.get_user().pk) + str(time.time()))
            self.save()

    def disable_private_slug(self):
        self.private_slug = None
        self.save()
