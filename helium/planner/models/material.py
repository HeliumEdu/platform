from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class Material(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    status = models.PositiveIntegerField(help_text='A valid material status choice.',
                                         choices=enums.MATERIAL_STATUS_CHOICES, default=enums.OWNED)

    condition = models.PositiveIntegerField(help_text='A valid material condition choice.',
                                            choices=enums.CONDITION_CHOICES, default=enums.BRAND_NEW)

    website = models.URLField(help_text='A valid URL.',
                              max_length=255, blank=True, null=True)

    # TODO: refactor to use a DecimalField instead of CharField
    price = models.CharField(help_text='A price string.',
                             max_length=255, blank=True, null=True)

    details = models.TextField(help_text='An arbitrary string (which may contain HTML formatting).',
                               default='', blank=True)

    # TODO: consider eliminating and just consolidating into 'details' depending on usage
    seller_details = models.TextField(help_text='An arbitrary string (which may contain HTML formatting).',
                                      default='', blank=True)

    material_group = models.ForeignKey('MaterialGroup', help_text='The material group with which to associate.',
                                       related_name='materials', on_delete=models.CASCADE)

    courses = models.ManyToManyField('Course', help_text='A list of courses with which to associate.',
                                     related_name='materials', blank=True, default=None)

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.material_group.get_user()
