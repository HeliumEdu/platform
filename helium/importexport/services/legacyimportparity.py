"""
Parity for import files written in an older export format.

Every legacy shape Helium still accepts on import is rewritten here into the current one, before
anything else reads the file, so no other import code knows a legacy shape exists. Ending support
for old files is deleting this module and its one call in `importservice`.
"""
import logging

from rest_framework.exceptions import ValidationError

from helium.common import enums
from helium.planner.serializers.noteserializer import NoteSerializer
from helium.planner.utils.quillutils import html_to_quill

logger = logging.getLogger(__name__)

_RENAMED_SECTIONS = (('material_groups', 'resource_groups'), ('materials', 'resources'))

_POPUP_AND_TEXT_REMINDER_TYPES = (0, 2)

_TEXT_FIELDS_NOW_NOTES = (('homework', 'comments', 'homework'),
                          ('events', 'comments', 'events'),
                          ('resources', 'details', 'resources'))


def upgrade_legacy_import(data):
    """
    Rewrite an import file from any older export format into the current one, in place.

    - `material_groups` / `materials` sections become `resource_groups` / `resources`; a Resource's
      `material_group` becomes `resource_group`; an Assignment's or Note's `materials` becomes `resources`.
    - Popup and Text reminders become Push reminders, and the exact duplicates that leaves (exports
      paired a Popup with a Push) are dropped.
    - Assignment and Event `comments` and Resource `details` text becomes an untitled Note linked to its
      item, unless the file already links a Note to that item, in which case the legacy text is dropped.

    :param data: The parsed import file.
    :return: The same file, in the current format.
    :raises ValidationError: If a row gives both a legacy key and its replacement, or legacy text is too
        large for a Note.
    """
    if not isinstance(data, dict):
        return data

    _rename_sections(data)
    errors = {}
    for row in _rows(data, 'resources'):
        _rename_key(row, 'material_group', 'resource_group')
    for section, singular in (('homework', 'homework row'), ('notes', 'note')):
        for row in _rows(data, section):
            if 'materials' in row and 'resources' in row:
                errors.setdefault(section, []).append(
                    f"Provide either 'resources' or 'materials' on a {singular}, not both.")
            _rename_key(row, 'materials', 'resources')
    _upgrade_reminders(data)
    _move_text_to_notes(data, errors)

    if errors:
        raise ValidationError(errors)

    return data


def _rows(data, section):
    rows = data.get(section)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _rename_key(row, old, new):
    if old in row:
        value = row.pop(old)
        row.setdefault(new, value)


def _rename_sections(data):
    for old, new in _RENAMED_SECTIONS:
        if old not in data:
            continue
        if new in data:
            raise ValidationError(f"Provide either '{new}' or '{old}', not both.")
        data[new] = data.pop(old)


def _upgrade_reminders(data):
    if not isinstance(data.get('reminders'), list):
        return

    upgraded = []
    seen = set()
    for reminder in data['reminders']:
        if isinstance(reminder, dict):
            if reminder.get('type') in _POPUP_AND_TEXT_REMINDER_TYPES:
                reminder['type'] = enums.PUSH
            key = tuple(str(reminder.get(field)) for field in (
                'homework', 'event', 'course', 'offset', 'offset_type', 'type', 'message', 'sent', 'dismissed'))
            if key in seen:
                continue
            seen.add(key)
        upgraded.append(reminder)
    data['reminders'] = upgraded


def _move_text_to_notes(data, errors):
    notes = data.get('notes', [])
    if not isinstance(notes, list):
        return

    next_note_id = max((_as_int(note.get('id')) for note in _rows(data, 'notes')), default=0) + 1
    for section, text_field, link_field in _TEXT_FIELDS_NOW_NOTES:
        already_linked = {str(item_id) for note in _rows(data, 'notes')
                          for item_id in (note.get(link_field) or []) if isinstance(note.get(link_field), list)}
        for row in _rows(data, section):
            text = row.pop(text_field, None)
            content = html_to_quill(text) if isinstance(text, str) else None
            if not content or str(row.get('id')) in already_linked:
                continue
            try:
                NoteSerializer().validate_content(content)
            except ValidationError as error:
                errors.setdefault(section, []).extend(
                    f"{section} id {row.get('id')}, {text_field}: {message}" for message in error.detail)
                continue
            notes.append({'id': next_note_id, 'title': '', 'content': content, link_field: [row.get('id')]})
            next_note_id += 1

    if notes:
        data['notes'] = notes


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
