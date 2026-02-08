__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.83"

import time

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from helium.common import enums
from helium.common.models import BaseModel
from helium.common.utils.validators import validate_hex_color


class UserSettings(BaseModel):
    time_zone = models.CharField(help_text='A valid time zone choice.',
                                 default='America/Los_Angeles', max_length=255, choices=enums.TIME_ZONE_CHOICES)

    default_view = models.PositiveIntegerField(help_text='A valid default calendar view choice.',
                                               choices=enums.VIEW_CHOICES, default=enums.MONTH)

    week_starts_on = models.PositiveIntegerField(help_text='A valid day on which the week should start choice.',
                                                 choices=enums.DAY_OF_WEEK_CHOICES, default=enums.SUNDAY)

    all_day_offset = models.PositiveIntegerField(default=30)

    show_getting_started = models.BooleanField(help_text='Whether the "Getting Started" dialog should be shown.',
                                               default=True)

    whats_new_version_seen = models.PositiveIntegerField(
        help_text='The "What\'s New" dialog version the user has seen.',
        default=0)

    events_color = models.CharField(
        help_text='A valid hex color code choice to determine the color events will be shown on the calendar.',
        max_length=7, validators=[validate_hex_color], default='#e74674')

    grade_color = models.CharField(
        help_text='A valid hex color code choice to determine the color grade badges will be.',
        max_length=7, validators=[validate_hex_color], default='#9d629d')

    material_color = models.CharField(
        help_text='A valid hex color code choice to determine the color material badges will be.',
        max_length=7, validators=[validate_hex_color], default='#dc7d50')

    calendar_event_limit = models.BooleanField(
        help_text='Whether calendar events should collapse to "+ more" when a day is full.',
        default=False)

    calendar_use_category_colors = models.BooleanField(
        help_text='Whether calendar items for classes should be shown in category colors instead of class colors.',
        default=False)

    default_reminder_type = models.PositiveIntegerField(
        help_text='A valid default type of reminder choice when creating a new reminder.',
        default=enums.PUSH, choices=enums.REMINDER_TYPE_CHOICES)

    default_reminder_offset = models.PositiveIntegerField(help_text='The default offset when creating a new reminder.',
                                                          default=30)

    default_reminder_offset_type = models.PositiveIntegerField(
        help_text='A valid default type of time offset choice when creating a new reminder.',
        default=enums.MINUTES,
        choices=enums.REMINDER_OFFSET_TYPE_CHOICES)

    receive_emails_from_admin = models.BooleanField(
        help_text='Whether the user wants to receive Helium update emails.',
        default=True)

    remember_filter_state = models.BooleanField(
        help_text='Remember filter states for the Calendar within a session.',
        default=True)

    color_scheme_theme = models.PositiveIntegerField(
        help_text='A valid color scheme theme.',
        default=enums.SYSTEM,
        choices=enums.COLOR_SCHEME_THEME)

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
