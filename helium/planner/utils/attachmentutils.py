__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import os
import uuid


def get_path_for_attachment(instance, filename):
    return os.path.join('attachments', str(instance.get_user().pk), uuid.uuid4().hex, filename)
