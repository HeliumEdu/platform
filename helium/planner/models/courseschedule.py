__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import datetime

from django.core import validators
from django.db import models

from helium.common.models import BaseModel
from helium.planner.managers.courseschedulemanager import CourseScheduleManager


class CourseSchedule(BaseModel):
    days_of_week = models.CharField(help_text='Seven booleans (0 or 1) indicating which days of the week the course is '
                                              'on (week starts on Sunday).',
                                    max_length=7, default='0000000', validators=[
            validators.RegexValidator(r'^[0-1]+$',
                                      'Seven booleans (0 or 1) indicating which days of the week the course is on '
                                      '(week starts on Sunday).',
                                      'invalid'),
            validators.MinLengthValidator(7,
                                          'Seven booleans (0 or 1) indicating which days of the week the course is on '
                                          '(week starts on Sunday).')])
    sun_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    sun_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    mon_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    mon_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    tue_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    tue_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    wed_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    wed_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    thu_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    thu_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    fri_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    fri_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    sat_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    sat_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='schedules', on_delete=models.CASCADE)

    objects = CourseScheduleManager()

    def __str__(self):  # pragma: no cover
        return str(f'{self.course.title}-{self.pk} ({self.get_user().get_username()})')

    def get_user(self):
        return self.course.get_user()
