from django.conf import settings
from django.db import models

from helium.common import enums
from helium.planner.models.basecalendar import BaseCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class Event(BaseCalendar):
    calendar_item_type = models.PositiveIntegerField(help_text='A valid calendar item choice.',
                                                     default=enums.EVENT, choices=enums.CALENDAR_ITEM_TYPE_CHOICES)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='events', on_delete=models.CASCADE)

    def get_user(self):
        return self.user
