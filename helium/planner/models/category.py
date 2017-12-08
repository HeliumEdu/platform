"""
Category model.
"""

from django.db import models

from helium.common import enums
from helium.planner.models.base import BasePlannerModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class Category(BasePlannerModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    weight = models.DecimalField(max_digits=5, decimal_places=2)

    color = models.CharField(max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    average_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    grade_by_weight = models.DecimalField(max_digits=7, default=0, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    course = models.ForeignKey('Course', related_name='categories', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ('title',)

    def __unicode__(self):
        return str('{} ({})'.format(self.title, self.get_user().get_username()))

    def get_user(self):
        return self.course.course_group.get_user()
