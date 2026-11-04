from django.db import models

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.resourcemanager import ResourceManager


class Resource(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255)

    status = models.PositiveIntegerField(help_text='The status of the resource.',
                                         choices=enums.RESOURCE_STATUS_CHOICES, default=enums.OWNED)

    condition = models.PositiveIntegerField(help_text='The physical condition of the resource.',
                                            choices=enums.CONDITION_CHOICES, default=enums.BRAND_NEW)

    website = models.URLField(help_text='A valid URL.',
                              max_length=3000, blank=True, null=True)

    price = models.CharField(help_text='A price string.',
                             max_length=255, blank=True)

    resource_group = models.ForeignKey('ResourceGroup', help_text='The resource group with which to associate.',
                                       related_name='resources', on_delete=models.CASCADE)

    courses = models.ManyToManyField('Course',
                                     help_text='Classes that share this resource. May be empty.',
                                     related_name='resources', blank=True, default=None)

    objects = ResourceManager()

    class Meta:
        verbose_name = 'Resource'
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.resource_group.get_user()

    @property
    def num_attachments(self):
        return self.attachments.count()
