from django.db import models

from helium.common.utils.commonutils import fraction_validator
from helium.common import enums
from helium.planner.models.basecalendar import BaseCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class Homework(BaseCalendar):
    current_grade = models.CharField(help_text='The current grade in fraction form (ex. 25/30).',
                                     max_length=255, validators=[fraction_validator])

    completed = models.BooleanField(help_text='Whether or not the homework has been completed.',
                                    default=False)

    calendar_item_type = models.PositiveIntegerField(default=enums.HOMEWORK,
                                                     choices=enums.CALENDAR_ITEM_TYPE_CHOICES)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='homework', on_delete=models.CASCADE)

    category = models.ForeignKey('Category', help_text='The category with which to associate.',
                                 related_name='homework', blank=True, null=True, default=None,
                                 on_delete=models.SET_NULL)

    materials = models.ManyToManyField('Material', help_text='A list of materials with which to associate.',
                                       related_name='homework', blank=True, default=None)

    def get_user(self):
        return self.course.get_user()
