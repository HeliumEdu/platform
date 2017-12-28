"""
MaterialGroup model.
"""

from django.conf import settings
from django.db import models

from helium.planner.models.base import BasePlannerModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class MaterialGroup(BasePlannerModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    shown_on_calendar = models.BooleanField(default=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='material_groups', on_delete=models.CASCADE)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return str('{} ({})'.format(self.title, self.get_user().get_username()))

    def get_user(self):
        return self.user
