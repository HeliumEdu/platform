"""
Course model.
"""
import datetime

from django.core import validators
from django.db import models

from helium.common import enums
from helium.planner.models.base import BasePlannerModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class Course(BasePlannerModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    room = models.CharField(max_length=255, default='', blank=True, null=True)

    credits = models.DecimalField(max_digits=4, decimal_places=2)

    color = models.CharField(max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    website = models.URLField(max_length=3000, blank=True, null=True)

    is_online = models.BooleanField(default=False)

    current_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    private_slug = models.SlugField(unique=True, blank=True, null=True)

    # TODO: teacher details will be abstracted into a Teacher model after the open source migration is finished
    teacher_name = models.CharField(max_length=255, default='', blank=True, null=True)

    teacher_email = models.EmailField(default='', blank=True, null=True)

    # TODO: these fields will be abstracted into a CourseSchedule model after the open source migration is finished
    start_date = models.DateField()
    end_date = models.DateField()
    days_of_week = models.CharField(max_length=7, default='0000000', validators=[
        validators.RegexValidator(r'^[0-1]+$',
                                  'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).',
                                  'invalid'),
        validators.MinLengthValidator(7,
                                      'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).')])
    sun_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    sun_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    mon_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    mon_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    tue_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    tue_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    wed_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    wed_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    thu_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    thu_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    fri_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    fri_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    sat_start_time = models.TimeField(default=datetime.time(12, 0, 0))
    sat_end_time = models.TimeField(default=datetime.time(12, 0, 0))
    # TODO: when CourseSchedule is created, it should simply be a foreign key relationship so "_alt" is no longer needed and any number of alt schedules can exist
    days_of_week_alt = models.CharField(max_length=7, default='0000000', validators=[
        validators.RegexValidator(r'^[0-1]+$',
                                  'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).',
                                  'invalid'),
        validators.MinLengthValidator(7,
                                      'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).')])
    sun_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    sun_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    mon_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    mon_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    tue_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    tue_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    wed_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    wed_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    thu_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    thu_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    fri_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    fri_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    sat_start_time_alt = models.TimeField(default=datetime.time(12, 0, 0))
    sat_end_time_alt = models.TimeField(default=datetime.time(12, 0, 0))

    course_group = models.ForeignKey('CourseGroup', related_name='courses', on_delete=models.CASCADE)

    class Meta:
        ordering = ('start_date',)

    def __unicode__(self):
        return str('{} ({})'.format(self.title, self.get_user().get_username()))

    def get_user(self):
        return self.course_group.get_user()
