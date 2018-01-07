from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.remindermanager import ReminderManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class Reminder(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    message = models.TextField(
        help_text='A string that will be used as the reminder message (may contain HTML formatting).')

    start_of_range = models.DateTimeField(help_text='An ISO-8601 date.')

    offset = models.PositiveIntegerField(help_text='The number of units (in `offset_type`) from the offset.',
                                         default=30)

    offset_type = models.PositiveIntegerField(help_text='A valid reminder offset type choice.',
                                              choices=enums.REMINDER_OFFSET_TYPE_CHOICES, default=enums.MINUTES)

    type = models.PositiveIntegerField(help_text='A valid reminder type choice.',
                                       choices=enums.REMINDER_TYPE_CHOICES, default=enums.POPUP)

    sent = models.BooleanField(default=False)

    from_admin = models.BooleanField(default=False)

    homework = models.ForeignKey('Homework', help_text='The homework with which to associate.',
                                 related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    event = models.ForeignKey('Event', help_text='The event with which to associate.',
                              related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reminders', db_index=True)

    objects = ReminderManager()

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.user
