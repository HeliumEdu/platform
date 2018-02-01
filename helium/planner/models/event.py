from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.planner.managers.eventmanager import EventManager
from helium.planner.models.basecalendar import BaseCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class Event(BaseCalendar):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='events', on_delete=models.CASCADE)

    objects = EventManager()

    class Meta:
        ordering = ('start',)

    def __init__(self, *args, **kwargs):
        self.__calendar_item_type = enums.EVENT if 'calendar_item_type' not in kwargs else kwargs['calendar_item_type']

        kwargs.pop('calendar_item_type', None)
        super(Event, self).__init__(*args, **kwargs)

    def get_user(self):
        return self.user

    @property
    def calendar_item_type(self):
        return self.__calendar_item_type
