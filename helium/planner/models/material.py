"""
Material model.
"""
import datetime

from django.core import validators
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.planner.models.base import BasePlannerModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class Material(BasePlannerModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    status = models.PositiveIntegerField(choices=enums.MATERIAL_STATUS_CHOICES, default=enums.OWNED)

    condition = models.PositiveIntegerField(choices=enums.CONDITION_CHOICES, default=enums.BRAND_NEW)

    website = models.URLField(max_length=255, blank=True, null=True)

    # TODO: refactor to use a DecimalField instead of CharField
    price = models.CharField(max_length=255, blank=True, null=True)

    details = models.TextField(default='', blank=True)

    # TODO: consider eliminating and just consolidating into 'details' depending on usage
    seller_details = models.TextField(default='', blank=True)

    material_group = models.ForeignKey('MaterialGroup', related_name='materials', on_delete=models.CASCADE)

    courses = models.ManyToManyField('Course', related_name='materials', blank=True, default=None)

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.material_group.get_user()
