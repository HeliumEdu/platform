__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel
from helium.planner.managers.materialgroupmanager import MaterialGroupManager


class MaterialGroup(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    shown_on_calendar = models.BooleanField(help_text='Whether or not items should be shown on the calendar.',
                                            default=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='material_groups', on_delete=models.CASCADE)

    objects = MaterialGroupManager()

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.user
