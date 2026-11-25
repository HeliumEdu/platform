import io
import logging
import os
import zipfile

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext
from rest_framework.exceptions import ValidationError

from helium.common import errorcodes

logger = logging.getLogger(__name__)

_ZIP_MAGIC = b'PK\x03\x04'

_READ_CHUNK_SIZE = 1024 * 1024


def _validate_extension(name):
    ext = os.path.splitext(name)[1].removeprefix('.').lower()
    if ext not in settings.FILE_TYPES:
        raise ValidationError(gettext('File type "%(ext)s" not supported.') % {'ext': ext},
                              code=errorcodes.FILE_TYPE_UNSUPPORTED)
    return ext


def _too_large_when_expanded():
    return ValidationError(
        gettext('The expanded archive exceeds the max import size of %(size)s.') % {
            'size': filesizeformat(settings.MAX_IMPORT_SIZE)}, code=errorcodes.ARCHIVE_TOO_LARGE)


def _archived_file(archive):
    entries = [entry for entry in archive.infolist()
               if not entry.is_dir()
               and not entry.filename.startswith('__MACOSX/')
               and not os.path.basename(entry.filename).startswith('._')]

    if len(entries) != 1:
        raise ValidationError(gettext('The archive must contain exactly one file.'), code=errorcodes.ARCHIVE_FILE_COUNT)

    entry = entries[0]
    if entry.flag_bits & 0x1:
        raise ValidationError(gettext('Encrypted archives are not supported.'), code=errorcodes.ARCHIVE_ENCRYPTED)
    if _validate_extension(entry.filename) == 'zip':
        raise ValidationError(gettext('The archive must not contain another archive.'), code=errorcodes.ARCHIVE_NESTED)

    return entry


def _read_archived(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entry = _archived_file(archive)

            # Declared sizes are attacker-controlled, so this only cheaply rejects honest
            # archives; the streaming read below is what bounds memory.
            if entry.file_size > settings.MAX_IMPORT_SIZE:
                raise _too_large_when_expanded()

            expanded = io.BytesIO()
            with archive.open(entry) as archived:
                while chunk := archived.read(_READ_CHUNK_SIZE):
                    expanded.write(chunk)
                    if expanded.tell() > settings.MAX_IMPORT_SIZE:
                        raise _too_large_when_expanded()

            return expanded.getvalue()
    except zipfile.BadZipFile:
        raise ValidationError(gettext('The archive could not be read.'), code=errorcodes.ARCHIVE_UNREADABLE)


def read(file) -> bytes:
    """
    The bytes of an uploaded import, transparently expanding a `.zip` so a backup too large to
    upload directly can still be restored. Everything is validated before the file is buffered.

    :param file: The uploaded file.
    :return: The file's bytes, expanded when it was an archive.
    :raises ValidationError: The file is too large, an unsupported type, or a malformed archive.
    """
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            gettext('The uploaded file exceeds the max upload size of %(size)s.') % {
                'size': filesizeformat(settings.MAX_UPLOAD_SIZE)}, code=errorcodes.FILE_TOO_LARGE)

    _validate_extension(file.name)

    data = b''.join(file.chunks())

    return _read_archived(data) if data[:4] == _ZIP_MAGIC else data
