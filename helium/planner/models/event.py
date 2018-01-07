from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.planner.managers.eventmanager import EventManager
from helium.planner.models.basecalendar import BaseCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class Event(BaseCalendar):
    # TODO: this value is constant and unnecessary to the database model type, so in the future it should be abstracted out to only be a serializer field
    calendar_item_type = models.PositiveIntegerField(help_text='A valid calendar item choice.',
                                                     default=enums.EVENT, choices=enums.CALENDAR_ITEM_TYPE_CHOICES)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='events', on_delete=models.CASCADE)

    objects = EventManager()

    class Meta:
        ordering = ('start',)

    def __str__(self):  # pragma: no cover
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.user
