__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from datetime import timedelta

import pytz
from django.conf import settings
from django.db import models

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.remindermanager import ReminderManager


class Reminder(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    message = models.TextField(
        help_text='A string that will be used as the reminder message (may contain HTML formatting).')

    start_of_range = models.DateTimeField(db_index=True)

    offset = models.PositiveIntegerField(help_text='The number of units (in `offset_type`) from the offset.',
                                         default=30)

    offset_type = models.PositiveIntegerField(help_text='A valid reminder offset type choice.',
                                              choices=enums.REMINDER_OFFSET_TYPE_CHOICES, default=enums.MINUTES)

    type = models.PositiveIntegerField(help_text='A valid reminder type choice.',
                                       choices=enums.REMINDER_TYPE_CHOICES, default=enums.POPUP, db_index=True)

    sent = models.BooleanField(help_text='Whether the reminder has been sent.', default=False, db_index=True)

    dismissed = models.BooleanField(help_text='Whether the reminder has been dismieed.', default=False, db_index=True)

    repeating = models.BooleanField(help_text='Whether the reminder repeats (for courses).', default=False)

    homework = models.ForeignKey('Homework', help_text='The homework with which to associate.',
                                 related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    event = models.ForeignKey('Event', help_text='The event with which to associate.',
                              related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='reminders', blank=True, null=True, on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reminders', on_delete=models.CASCADE)

    objects = ReminderManager()

    class Meta:
        ordering = ('start_of_range', 'title')

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.user

    def _get_next_course_occurrence_start(self):
        """
        Calculate the next occurrence start time for a course.
        Returns None if no future occurrence exists within the course date range.
        """
        course = self.course
        course_schedule = course.schedules.first()
        if not course_schedule:
            return None

        user_tz = pytz.timezone(course.get_user().settings.time_zone)
        now = datetime.datetime.now(user_tz)
        today = now.date()

        # Start from today or course start_date, whichever is later
        day = max(today, course.start_date)

        # Look through days until we find the next occurrence or pass end_date
        while day <= course.end_date:
            weekday = enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()]

            if course_schedule.days_of_week[weekday] == "1":
                # Get the start time for this weekday
                start_time = getattr(course_schedule, f'{["sun", "mon", "tue", "wed", "thu", "fri", "sat"][weekday]}_start_time')

                # Combine date and time in user's timezone
                local_start = user_tz.localize(datetime.datetime.combine(day, start_time))

                # Only return if this occurrence is in the future
                if local_start > now:
                    return local_start.astimezone(pytz.utc)

            day += datetime.timedelta(days=1)

        return None

    def save(self, *args, **kwargs):
        """
        Updated start_of_range based on the start time for the calendar item.
        """
        if self.homework:
            calendar_item = self.homework
        elif self.event:
            calendar_item = self.event
        else:
            calendar_item = None

        if calendar_item:
            self.start_of_range = calendar_item.start - timedelta(
                **{enums.REMINDER_OFFSET_TYPE_CHOICES[self.offset_type][1]: int(self.offset)})
        elif self.course:
            next_start = self._get_next_course_occurrence_start()
            if next_start:
                self.start_of_range = next_start - timedelta(
                    **{enums.REMINDER_OFFSET_TYPE_CHOICES[self.offset_type][1]: int(self.offset)})

        super().save(*args, **kwargs)
