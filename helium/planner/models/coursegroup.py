import datetime

from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common.models import BaseModel
from helium.planner.managers.coursegroupmanager import CourseGroupManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class CourseGroup(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    start_date = models.DateField(help_text='An ISO-8601 date.')

    end_date = models.DateField(help_text='An ISO-8601 date.')

    shown_on_calendar = models.BooleanField(help_text='Whether or not items should be shown on the calendar.',
                                            default=True)

    average_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    private_slug = models.SlugField(unique=True, blank=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='course_groups', on_delete=models.CASCADE)

    objects = CourseGroupManager()

    class Meta:
        ordering = ('start_date',)

    def __str__(self):  # pragma: no cover
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.user

    @property
    def percent_thru(self):
        num_days = (self.end_date - self.start_date).days
        days_completed = (datetime.datetime.now().date() - self.start_date).days

        return (float(days_completed) / float(num_days)) * 100 if num_days > 0 \
            else (0 if self.days_remaining > 0 else 100)

    @property
    def days_remaining(self):
        return (self.end_date - datetime.datetime.now().date()).days

    @property
    def num_items(self):
        count = 0
        for course in self.courses.iterator():
            count += course.num_items
        return count

    @property
    def num_complete(self):
        count = 0
        for course in self.courses.iterator():
            count += course.num_complete
        return count

    @property
    def num_incomplete(self):
        count = 0
        for course in self.courses.iterator():
            count += course.num_incomplete
        return count

    @property
    def num_graded(self):
        count = 0
        for course in self.courses.iterator():
            count += course.num_graded
        return count
