"""
Course model.
"""
from django.core import validators
from django.db import models
from django.utils import timezone

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
    sun_start_time = models.TimeField(blank=True, null=True)
    sun_end_time = models.TimeField(blank=True, null=True)
    mon_start_time = models.TimeField(blank=True, null=True)
    mon_end_time = models.TimeField(blank=True, null=True)
    tue_start_time = models.TimeField(blank=True, null=True)
    tue_end_time = models.TimeField(blank=True, null=True)
    wed_start_time = models.TimeField(blank=True, null=True)
    wed_end_time = models.TimeField(blank=True, null=True)
    thu_start_time = models.TimeField(blank=True, null=True)
    thu_end_time = models.TimeField(blank=True, null=True)
    fri_start_time = models.TimeField(blank=True, null=True)
    fri_end_time = models.TimeField(blank=True, null=True)
    sat_start_time = models.TimeField(blank=True, null=True)
    sat_end_time = models.TimeField(blank=True, null=True)
    # TODO: when CourseSchedule is created, it should simply be a foreign key relationship so "_alt" is no longer needed and any number of alt schedules can exist
    sun_start_time_alt = models.TimeField(blank=True, null=True)
    sun_end_time_alt = models.TimeField(blank=True, null=True)
    mon_start_time_alt = models.TimeField(blank=True, null=True)
    mon_end_time_alt = models.TimeField(blank=True, null=True)
    tue_start_time_alt = models.TimeField(blank=True, null=True)
    tue_end_time_alt = models.TimeField(blank=True, null=True)
    wed_start_time_alt = models.TimeField(blank=True, null=True)
    wed_end_time_alt = models.TimeField(blank=True, null=True)
    thu_start_time_alt = models.TimeField(blank=True, null=True)
    thu_end_time_alt = models.TimeField(blank=True, null=True)
    fri_start_time_alt = models.TimeField(blank=True, null=True)
    fri_end_time_alt = models.TimeField(blank=True, null=True)
    sat_start_time_alt = models.TimeField(blank=True, null=True)
    sat_end_time_alt = models.TimeField(blank=True, null=True)

    course_group = models.ForeignKey('CourseGroup', related_name='courses', on_delete=models.CASCADE)

    def __unicode__(self):
        return str('{} ({})'.format(self.title, self.get_user().get_username()))

    def get_user(self):
        return self.course_group.get_user()
