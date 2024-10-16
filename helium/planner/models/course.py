__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import datetime

from django.db import models

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.coursemanager import CourseManager


class Course(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    room = models.CharField(help_text='An arbitrary string.',
                            max_length=255, blank=True)

    credits = models.DecimalField(help_text='A decimal corresponding to credit hours.',
                                  max_digits=4, decimal_places=2)

    color = models.CharField(
        help_text='A valid hex color code choice to determine the color events will be shown on the calendar',
        max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    website = models.URLField(help_text='A valid URL.', max_length=3000, blank=True, null=True)

    is_online = models.BooleanField(
        help_text='Whether or not the course is online (and thus may have times associated with it)',
        default=False)

    current_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    teacher_name = models.CharField(help_text='A display name for the teacher.',
                                    max_length=255, blank=True)

    teacher_email = models.EmailField(help_text='A valid email address.',
                                      default=None, blank=True, null=True)

    start_date = models.DateField(help_text='An ISO-8601 date.',
                                  db_index=True)
    end_date = models.DateField(help_text='An ISO-8601 date.',
                                db_index=True)

    course_group = models.ForeignKey('CourseGroup', help_text='The course group with which to associate.',
                                     related_name='courses', on_delete=models.CASCADE)

    objects = CourseManager()

    class Meta:
        ordering = ('start_date', 'title')

    def __str__(self):  # pragma: no cover
        return str(f'{self.title} ({self.get_user().get_username()})')

    def get_user(self):
        return self.course_group.get_user()

    @property
    def num_days(self):
        return (self.end_date - self.start_date).days

    @property
    def num_days_completed(self):
        return (datetime.datetime.now().date() - self.start_date).days

    @property
    def has_weighted_grading(self):
        return Course.objects.has_weighted_grading(self.pk)

    @property
    def num_homework(self):
        return self.homework.count()

    @property
    def num_homework_completed(self):
        return self.homework.completed().count()

    @property
    def num_homework_graded(self):
        return self.homework.graded().count()
