__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging
import os

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


def read(file):
    json_str = b''
    for chunk in file.chunks():
        json_str += chunk

    ext = os.path.splitext(file.name)[1].lstrip('.')
    if ext not in settings.FILE_TYPES:
        raise ValidationError(f'File type "{ext}" not supported.')

    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            f'The uploaded file exceeds the max upload size of {filesizeformat(settings.MAX_UPLOAD_SIZE)}.')

    return json_str
