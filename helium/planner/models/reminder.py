__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from datetime import timedelta

import pytz
from django.conf import settings
from django.db import models
from django.utils import timezone

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.remindermanager import ReminderManager


class Reminder(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    message = models.TextField(
        help_text='A string that will be used as the reminder message (may contain HTML formatting).')

    start_of_range = models.DateTimeField(db_index=True, null=True, blank=True)

    offset = models.PositiveIntegerField(help_text='The number of units (in `offset_type`) from the offset.',
                                         default=30)

    offset_type = models.PositiveIntegerField(help_text='A valid reminder offset type choice.',
                                              choices=enums.REMINDER_OFFSET_TYPE_CHOICES, default=enums.MINUTES)

    type = models.PositiveIntegerField(help_text='A valid reminder type choice.',
                                       choices=enums.REMINDER_TYPE_CHOICES, default=enums.POPUP, db_index=True)

    sent = models.BooleanField(help_text='Whether the reminder has been sent.', default=False, db_index=True)

    dismissed = models.BooleanField(help_text='Whether the reminder has been dismissed.', default=False, db_index=True)

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

    def _parse_exceptions(self):
        """
        Parse exception dates from course and course group.
        Returns a set of dates when the course does not meet.
        """
        exceptions = set()

        # Group-level exceptions (holidays, breaks)
        if self.course.course_group.exceptions:
            for date_str in self.course.course_group.exceptions.split(','):
                date_str = date_str.strip()
                if date_str:
                    try:
                        exceptions.add(datetime.datetime.strptime(date_str, '%Y%m%d').date())
                    except ValueError:
                        pass  # Skip invalid date formats

        # Course-level exceptions (professor cancellations)
        if self.course.exceptions:
            for date_str in self.course.exceptions.split(','):
                date_str = date_str.strip()
                if date_str:
                    try:
                        exceptions.add(datetime.datetime.strptime(date_str, '%Y%m%d').date())
                    except ValueError:
                        pass  # Skip invalid date formats

        return exceptions

    def _get_next_course_occurrence_start(self, after_datetime=None):
        """
        Calculate the next occurrence start time for a course.

        When after_datetime is provided (e.g. the start time of the class that just fired), the
        search finds the first class that starts strictly after that point, with no send-window
        staleness check. This is used by create_next_repeating_reminder to guarantee the newly
        queued reminder targets the *next* class, never the one that just fired.

        When after_datetime is None (creation / recalculation context), the normal behaviour
        applies: find the next class whose reminder time (class_start - offset) has not already
        expired past the send window.

        Returns None if no qualifying future occurrence exists within the course date range.
        """
        course = self.course
        course_schedules = list(course.schedules.all())
        if not course_schedules:
            return None

        user_tz = pytz.timezone(course.get_user().settings.time_zone)
        now = datetime.datetime.now(user_tz)
        today = now.date()

        if after_datetime is not None:
            cutoff = after_datetime.astimezone(user_tz)
            use_window_check = False
        else:
            cutoff = now
            use_window_check = True

        exceptions = self._parse_exceptions()
        day = max(today, course.start_date)
        day_names = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]

        while day <= course.end_date:
            if day in exceptions:
                day += datetime.timedelta(days=1)
                continue

            weekday = enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()]

            active_schedule = next(
                (s for s in course_schedules if s.days_of_week[weekday] == "1"),
                None,
            )
            if active_schedule:
                start_time = getattr(active_schedule, f'{day_names[weekday]}_start_time')
                local_start = user_tz.localize(datetime.datetime.combine(day, start_time))

                if use_window_check:
                    offset_delta = datetime.timedelta(
                        **{enums.REMINDER_OFFSET_TYPE_CHOICES[self.offset_type][1]: int(self.offset)})
                    window_start = now - datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES)
                    if local_start > now and (local_start - offset_delta) >= window_start:
                        return local_start.astimezone(pytz.utc)
                else:
                    if local_start > cutoff:
                        return local_start.astimezone(pytz.utc)

            day += datetime.timedelta(days=1)

        return None

    def save(self, *args, **kwargs):
        """
        Recalculate start_of_range based on the linked calendar item.

        For homework and event reminders, start_of_range is always recalculated so that
        moving a due date or event time is reflected immediately. If the recalculated
        start_of_range falls within or after the send window (i.e. the reminder hasn't
        meaningfully expired), a previously-sent reminder is reset to sent=False so it
        re-fires at the new time. Reminders whose start_of_range lands more than
        REMINDER_SEND_WINDOW_MINUTES in the past are left as-is — the window acts as the
        natural guard against re-fires for trivial date nudges.

        Course reminders retain the sent=False gate because their recalculation logic is
        being refactored separately.

        For course reminders with no qualifying future occurrence, start_of_range is set to
        None — the series becomes inactive until the course schedule changes, at which point
        the adjust_reminder_times signal triggers a fresh recalculation.
        """
        if self.homework or self.event:
            calendar_item = self.homework or self.event
            offset_delta = timedelta(**{enums.REMINDER_OFFSET_TYPE_CHOICES[self.offset_type][1]: int(self.offset)})
            new_start_of_range = calendar_item.start - offset_delta
            if self.pk and self.sent and new_start_of_range != self.start_of_range:
                window_start = timezone.now() - timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES)
                if new_start_of_range >= window_start:
                    self.sent = False
            self.start_of_range = new_start_of_range
        elif self.course and not self.sent:
            next_start = self._get_next_course_occurrence_start()
            if next_start:
                self.start_of_range = next_start - timedelta(
                    **{enums.REMINDER_OFFSET_TYPE_CHOICES[self.offset_type][1]: int(self.offset)})
            else:
                self.start_of_range = None

        super().save(*args, **kwargs)
