__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime

from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.courseschedulemanager import CourseScheduleManager


class CourseSchedule(BaseModel):
    days_of_week = models.CharField(help_text='Seven booleans (0 or 1) indicating which days of the week the course is '
                                              'on (week starts on Sunday). Authoritative — a `0` short-circuits event '
                                              'generation regardless of the per-day time fields. See "Common pitfalls" '
                                              'in the API description for the `00:00:00` off-day convention.',
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

    cycle_length = models.PositiveSmallIntegerField(
        help_text='The number of school days in one rotation cycle (mutually exclusive with `week_interval`).',
        blank=True, null=True)

    anchor_date = models.DateField(
        help_text='ISO-8601 date a rotation is anchored to.',
        blank=True, null=True)

    cycle_slots = models.JSONField(
        help_text='A day-based cycle\'s meeting times keyed by cycle-day index, as a list of '
                  '`{"indices": [...], "start_time": "HH:MM:SS", "end_time": "HH:MM:SS"}`.',
        blank=True, null=True)

    week_interval = models.PositiveSmallIntegerField(
        help_text='The number of weeks in one rotation for a week-based schedule '
                  '(mutually exclusive with `cycle_length`).',
        blank=True, null=True)

    week_offset = models.PositiveSmallIntegerField(
        help_text="Which week of the rotation this schedule meets, counted from `anchor_date`'s week.",
        blank=True, null=True)

    start_date = models.DateField(
        help_text="ISO-8601 date for schedule start override; when not set, the course's `start_date` is used.",
        blank=True, null=True)

    end_date = models.DateField(
        help_text="ISO-8601 date for schedule end override; when not set, the course's `end_date` is used.",
        blank=True, null=True)

    template = models.PositiveSmallIntegerField(
        help_text='The template this schedule was created from.',
        choices=enums.SCHEDULE_TEMPLATE_CHOICES, blank=True, null=True)

    objects = CourseScheduleManager()

    class Meta:
        verbose_name = 'Class schedule'
        constraints = [
            models.CheckConstraint(
                check=~(Q(cycle_length__isnull=False) & Q(week_interval__isnull=False)),
                name='courseschedule_single_rotation_type',
            ),
        ]

    @property
    def is_cycle(self):
        return self.cycle_length is not None

    @property
    def is_week_based(self):
        return self.week_interval is not None

    @property
    def is_rotating(self):
        """A cycle (day-based) or week-based rotation — i.e. anything a pre-advanced client can't render."""
        return self.is_cycle or self.is_week_based

    def clean(self):
        super().clean()
        for day in ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'):
            start_time = getattr(self, f'{day}_start_time')
            end_time = getattr(self, f'{day}_end_time')
            if start_time and end_time and start_time > end_time:
                raise ValidationError(f"The 'start_time' of '{day}' must be before 'end_time'")

    def __str__(self):  # pragma: no cover
        return str(f'{self.course.title}-{self.pk} ({self.get_user().get_username()})')

    def get_user(self):
        return self.course.get_user()
