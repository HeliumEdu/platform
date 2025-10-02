__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

from django.conf import settings
from django.db import models

from helium.common import enums
from helium.planner.managers.eventmanager import EventManager
from helium.planner.models.basecalendar import BaseCalendar


class Event(BaseCalendar):
    owner_id = models.CharField(help_text='An arbitrary string identifying the owning resource.',
                                max_length=255, blank=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='events', on_delete=models.CASCADE)

    objects = EventManager()

    class Meta:
        ordering = ('start', 'title')

    def __init__(self, *args, **kwargs):
        self.__calendar_item_type = enums.EVENT if 'calendar_item_type' not in kwargs else kwargs['calendar_item_type']

        kwargs.pop('calendar_item_type', None)
        super().__init__(*args, **kwargs)

    def get_user(self):
        return self.user

    @property
    def calendar_item_type(self) -> int:
        return self.__calendar_item_type
