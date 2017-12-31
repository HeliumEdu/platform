from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from helium.common.models import BaseModel
from helium.common.utils.commonutils import HeliumError

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class AttachmentError(HeliumError):
    pass


class Attachment(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    attachment = models.FileField(help_text='The file to be uploaded.',
                                  upload_to='attachments', blank=True, null=True)

    size = models.PositiveIntegerField(default=0)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='attachments', blank=True, null=True, on_delete=models.CASCADE)

    # TODO: uncomment (and rerun `make migrations`) when these models have been implemented
    # event = models.ForeignKey('Event', related_name='attachments', blank=True, null=True, on_delete=models.CASCADE)

    # homework = models.ForeignKey('Homework', related_name='attachments', blank=True, null=True, on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='attachments', on_delete=models.CASCADE)

    def get_user(self):
        if self.course:
            return self.course.get_user()
        elif self.event:
            return self.event.get_user()
        elif self.homework:
            return self.homework.get_user()

        raise AttachmentError('Attachment {} is not associated with any models.'.format(self.pk))

    def save(self, *args, **kwargs):
        """
        Call the super save, but also make any uploaded attachments private on S3.
        """
        self.size = self.attachment.size if self.attachment else 0

        super(Attachment, self).save(*args, **kwargs)

        # TODO: if uploaded to S3, code must be implemented here to make the file private by default


@receiver(post_delete, sender=Attachment)
def delete_attachment(sender, instance, **kwargs):
    """
    Delete the associated file in storage, if it exists.
    """
    if instance.attachment:
        instance.attachment.delete(False)
