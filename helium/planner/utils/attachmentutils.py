import os
import uuid

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


def get_path_for_attachment(instance, filename):
    return os.path.join('attachments', str(instance.get_user().pk), uuid.uuid4().hex, filename)
