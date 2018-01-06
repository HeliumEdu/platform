from django.conf import settings
from django.db import models

from helium.common import enums
from helium.planner.managers.eventmanager import EventManager
from helium.planner.models.basecalendar import BaseCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class Event(BaseCalendar):
    # TODO: this value is constant and unnecessary to the database model type, so in the future it should be abstracted out to only be a serializer field
    calendar_item_type = models.PositiveIntegerField(help_text='A valid calendar item choice.',
                                                     default=enums.EVENT, choices=enums.CALENDAR_ITEM_TYPE_CHOICES)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='events', on_delete=models.CASCADE)

    objects = EventManager()

    def get_user(self):
        return self.user
