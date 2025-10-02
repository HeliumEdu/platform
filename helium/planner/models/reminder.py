__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from datetime import timedelta

from django.conf import settings
from django.db import models

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.remindermanager import ReminderManager


class Reminder(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    message = models.TextField(
        help_text='A string that will be used as the reminder message (may contain HTML formatting).')

    start_of_range = models.DateTimeField(db_index=True)

    offset = models.PositiveIntegerField(help_text='The number of units (in `offset_type`) from the offset.',
                                         default=30)

    offset_type = models.PositiveIntegerField(help_text='A valid reminder offset type choice.',
                                              choices=enums.REMINDER_OFFSET_TYPE_CHOICES, default=enums.MINUTES)

    type = models.PositiveIntegerField(help_text='A valid reminder type choice.',
                                       choices=enums.REMINDER_TYPE_CHOICES, default=enums.POPUP, db_index=True)

    sent = models.BooleanField(help_text='Whether or not the reminder has been sent.', default=False, db_index=True)

    homework = models.ForeignKey('Homework', help_text='The homework with which to associate.',
                                 related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    event = models.ForeignKey('Event', help_text='The event with which to associate.',
                              related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reminders', on_delete=models.CASCADE)

    objects = ReminderManager()

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.user

    def save(self, *args, **kwargs):
        """
        Updated start_of_range based on the start time for the calendar item.
        """
        if self.homework:
            calendar_item = self.homework
        else:
            calendar_item = self.event

        if calendar_item:
            self.start_of_range = calendar_item.start - timedelta(
                **{enums.REMINDER_OFFSET_TYPE_CHOICES[self.offset_type][1]: int(self.offset)})

        super().save(*args, **kwargs)
