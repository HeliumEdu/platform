import datetime

from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common.models import BaseModel
from helium.planner.managers.coursegroupmanager import CourseGroupManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.2'


@python_2_unicode_compatible
class CourseGroup(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    start_date = models.DateField(help_text='An ISO-8601 date.',
                                  db_index=True)

    end_date = models.DateField(help_text='An ISO-8601 date.',
                                db_index=True)

    shown_on_calendar = models.BooleanField(help_text='Whether or not items should be shown on the calendar.',
                                            default=True, db_index=True)

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
    def num_days(self):
        return (self.end_date - self.start_date).days

    @property
    def num_days_completed(self):
        return (datetime.datetime.now().date() - self.start_date).days

    @property
    def num_homework(self):
        return self.courses.num_homework()

    @property
    def num_homework_completed(self):
        return self.courses.num_homework_completed()

    @property
    def num_homework_graded(self):
        return self.courses.num_homework_graded()
