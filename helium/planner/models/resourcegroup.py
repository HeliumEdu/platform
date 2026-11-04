from django.conf import settings
from django.db import models

from helium.common.models import BaseModel
from helium.planner.managers.resourcegroupmanager import ResourceGroupManager


class ResourceGroup(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255)

    shown_on_calendar = models.BooleanField(help_text='Whether items should be shown on the calendar.',
                                            default=True)

    example_schedule = models.BooleanField(help_text='Whether it is part of the example schedule.',
                                           default=False)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='resource_groups', on_delete=models.CASCADE)

    objects = ResourceGroupManager()

    class Meta:
        verbose_name = 'Resource group'
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.user

    @property
    def num_resources(self) -> int:
        return self.resources.count()

    @property
    def num_attachments(self):
        return self.resources.num_attachments()
