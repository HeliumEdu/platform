from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class Category(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    weight = models.DecimalField(
        help_text='A decimal weight for this category\'s homework (note that all weights associated with a single '
                  'course cannot exceed a value of 100).',
        max_digits=5, decimal_places=2)

    color = models.CharField(help_text='A hex color code to determine the color items will be shown on the calendar',
                             max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    average_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    grade_by_weight = models.DecimalField(max_digits=7, default=0, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='categories', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ('title',)

    def __str__(self):
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.course.course_group.get_user()
