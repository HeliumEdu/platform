__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.33"

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel
from helium.common.utils.commonutils import HeliumError
from helium.planner.managers.attachmentmanager import AttachmentManager
from helium.planner.utils.attachmentutils import get_path_for_attachment


class AttachmentError(HeliumError):
    pass


class Attachment(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    attachment = models.FileField(help_text='The file to be uploaded.',
                                  upload_to=get_path_for_attachment, blank=True, null=True)

    size = models.PositiveIntegerField(default=0)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='attachments', blank=True, null=True, on_delete=models.CASCADE)

    event = models.ForeignKey('Event', help_text='The event with which to associate.',
                              related_name='attachments', blank=True, null=True, on_delete=models.CASCADE)

    homework = models.ForeignKey('Homework', help_text='The homework with which to associate.',
                                 related_name='attachments', blank=True, null=True, on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='attachments', on_delete=models.CASCADE)

    objects = AttachmentManager()

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        if self.course:
            return self.course.get_user()
        elif self.event:
            return self.event.get_user()
        elif self.homework:
            return self.homework.get_user()

        raise AttachmentError(f'Attachment {self.pk} is not associated with any models.')

    def save(self, *args, **kwargs):
        """
        Call the super save, but also make any uploaded attachments private on S3.
        """
        self.size = self.attachment.size if self.attachment else 0

        super().save(*args, **kwargs)
