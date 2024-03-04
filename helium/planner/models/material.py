__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from django.db import models

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.materialmanager import MaterialManager


class Material(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    status = models.PositiveIntegerField(help_text='A valid material status choice.',
                                         choices=enums.MATERIAL_STATUS_CHOICES, default=enums.OWNED)

    condition = models.PositiveIntegerField(help_text='A valid material condition choice.',
                                            choices=enums.CONDITION_CHOICES, default=enums.BRAND_NEW)

    website = models.URLField(help_text='A valid URL.',
                              max_length=3000, blank=True, null=True)

    price = models.CharField(help_text='A price string.',
                             max_length=255, blank=True)

    details = models.TextField(help_text='An arbitrary string (which may contain HTML formatting).',
                               blank=True)

    material_group = models.ForeignKey('MaterialGroup', help_text='The material group with which to associate.',
                                       related_name='materials', on_delete=models.CASCADE)

    courses = models.ManyToManyField('Course', help_text='A list of courses with which to associate.',
                                     related_name='materials', blank=True, default=None)

    objects = MaterialManager()

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.material_group.get_user()
