"""
CourseGroup model.
"""

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class CourseGroup(BaseModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    start_date = models.DateField()

    end_date = models.DateField()

    shown_on_calendar = models.BooleanField(default=True)

    average_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    private_slug = models.SlugField(unique=True, blank=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='course_groups', on_delete=models.CASCADE)

    def __unicode__(self):
        return str('{} ({})'.format(self.title, self.user.get_username()))
