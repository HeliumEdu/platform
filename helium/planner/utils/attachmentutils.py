__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os
import uuid


def get_path_for_attachment(instance, filename):
    return os.path.join('attachments', str(instance.get_user().pk), uuid.uuid4().hex, filename)
