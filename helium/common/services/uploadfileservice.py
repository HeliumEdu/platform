import logging
import os

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from rest_framework.exceptions import ValidationError

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

logger = logging.getLogger(__name__)


def read(file):
    json_str = b''
    for chunk in file.chunks():
        json_str += chunk

    ext = os.path.splitext(file.name)[1].lstrip('.')
    if ext not in settings.FILE_TYPES:
        raise ValidationError('File type "{}" not supported.'.format(ext))

    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            'The uploaded file exceeds the max upload size of {}.'.format(filesizeformat(settings.MAX_UPLOAD_SIZE)))

    return json_str
