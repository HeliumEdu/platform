__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

"""
One-time migration to convert ALL legacy notes to the new Note system.

This migration:
1. Converts `comments` (Homework/Event) and `details` (Material) from HTML to Quill JSON
2. Saves to the `notes` field on each entity
3. Creates Note + NoteLink entries for each

Migration 0026 only migrated items that already had `notes` content. This migration
catches all legacy-only items that were missed.
"""

import re
from html.parser import HTMLParser

from django.db import migrations


def html_to_quill(html):
    """
    Convert HTML string to Quill Delta format.

    Returns a dict with 'ops' key containing the list of operations,
    or None if the input is empty/blank.
    """
    if not html or not html.strip():
        return None

    parser = _QuillHTMLParser()
    parser.feed(html)
    ops = parser.ops

    if not ops:
        return None

    # Quill requires documents to end with a newline
    if ops and ops[-1].get('insert') != '\n':
        ops.append({'insert': '\n'})

    return {'ops': ops}


class _QuillHTMLParser(HTMLParser):
    """HTML parser that builds Quill Delta operations."""

    def __init__(self):
        super().__init__()
        self.ops = []
        self._attr_stack = [{}]
        self._block_stack = []
        self._list_type_stack = []

    def _current_attrs(self):
        return self._attr_stack[-1].copy()

    def _push_attrs(self, new_attrs):
        merged = self._current_attrs()
        merged.update(new_attrs)
        self._attr_stack.append(merged)

    def _pop_attrs(self):
        if len(self._attr_stack) > 1:
            self._attr_stack.pop()

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        inline_attrs = {}
        block_attrs = None
        is_block = False

        if tag in ('strong', 'b'):
            inline_attrs['bold'] = True
        elif tag in ('em', 'i'):
            inline_attrs['italic'] = True
        elif tag == 'u':
            inline_attrs['underline'] = True
        elif tag in ('s', 'strike', 'del'):
            inline_attrs['strike'] = True
        elif tag == 'a':
            href = attrs_dict.get('href')
            if href:
                inline_attrs['link'] = href
        elif tag == 'br':
            self.ops.append({'insert': '\n'})
            return
        elif tag == 'font':
            color = attrs_dict.get('color')
            if color:
                inline_attrs['color'] = _normalize_color(color)
            face = attrs_dict.get('face')
            if face:
                inline_attrs['font'] = _normalize_font_name(face)
        elif tag == 'span':
            style = attrs_dict.get('style')
            if style:
                inline_attrs.update(_parse_inline_styles(style))
        elif tag in ('p', 'div'):
            is_block = True
        elif tag == 'h1':
            is_block = True
            block_attrs = {'header': 1}
        elif tag == 'h2':
            is_block = True
            block_attrs = {'header': 2}
        elif tag == 'h3':
            is_block = True
            block_attrs = {'header': 3}
        elif tag == 'h4':
            is_block = True
            block_attrs = {'header': 4}
        elif tag == 'h5':
            is_block = True
            block_attrs = {'header': 5}
        elif tag == 'h6':
            is_block = True
            block_attrs = {'header': 6}
        elif tag == 'blockquote':
            is_block = True
            block_attrs = {'blockquote': True}
        elif tag == 'ul':
            self._list_type_stack.append('bullet')
            return
        elif tag == 'ol':
            self._list_type_stack.append('ordered')
            return
        elif tag == 'li':
            is_block = True
            list_type = self._list_type_stack[-1] if self._list_type_stack else 'bullet'
            block_attrs = {'list': list_type}

        if inline_attrs:
            self._push_attrs(inline_attrs)
        else:
            self._push_attrs({})

        if is_block:
            self._block_stack.append((tag, block_attrs))

    def handle_endtag(self, tag):
        if tag in ('ul', 'ol'):
            if self._list_type_stack:
                self._list_type_stack.pop()
            return

        if self._block_stack and self._block_stack[-1][0] == tag:
            _, block_attrs = self._block_stack.pop()
            block_op = {'insert': '\n'}
            if block_attrs:
                block_op['attributes'] = block_attrs
            self.ops.append(block_op)

        self._pop_attrs()

    def handle_data(self, data):
        if not data:
            return
        attrs = self._current_attrs()
        op = {'insert': data}
        if attrs:
            op['attributes'] = attrs
        self.ops.append(op)

    def handle_entityref(self, name):
        from html import unescape
        char = unescape(f'&{name};')
        self.handle_data(char)

    def handle_charref(self, name):
        from html import unescape
        char = unescape(f'&#{name};')
        self.handle_data(char)


def _parse_inline_styles(style):
    attrs = {}
    if not style:
        return attrs

    for declaration in style.split(';'):
        if ':' not in declaration:
            continue
        prop, value = declaration.split(':', 1)
        prop = prop.strip().lower()
        value = value.strip()

        if prop == 'color':
            attrs['color'] = _normalize_color(value)
        elif prop == 'background-color':
            attrs['background'] = _normalize_color(value)
        elif prop == 'font-family':
            attrs['font'] = _normalize_font_name(value)

    return attrs


def _normalize_color(value):
    match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', value)
    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return f'#{r:02x}{g:02x}{b:02x}'
    return value


def _normalize_font_name(value):
    first_font = value.split(',')[0].strip()
    return first_font.replace('"', '').replace("'", '').lower()


def migrate_legacy_notes_forward(apps, schema_editor):
    """
    Migrate all legacy HTML notes to Quill JSON format.

    For items that:
    - Have non-empty `comments` (Homework/Event) or `details` (Material)
    - Don't already have a NoteLink (weren't caught by migration 0026)

    This creates:
    1. Quill JSON in the `notes` field
    2. A Note entry in the Note table
    3. A NoteLink connecting them
    """
    Note = apps.get_model('planner', 'Note')
    NoteLink = apps.get_model('planner', 'NoteLink')
    Homework = apps.get_model('planner', 'Homework')
    Event = apps.get_model('planner', 'Event')
    Material = apps.get_model('planner', 'Material')

    # Migrate Homework with comments but no NoteLink
    homework_qs = (
        Homework.objects
        .select_related('course__course_group')
        .exclude(comments='')
        .filter(note_links__isnull=True)
    )
    for hw in homework_qs:
        quill = html_to_quill(hw.comments)
        if not quill:
            continue

        hw.notes = quill
        hw.save(update_fields=['notes'])

        note = Note.objects.create(
            title=f'Notes for: {hw.title}',
            content=quill,
            user_id=hw.course.course_group.user_id,
        )
        NoteLink.objects.create(note=note, homework=hw)

    # Migrate Event with comments but no NoteLink
    event_qs = (
        Event.objects
        .exclude(comments='')
        .filter(note_links__isnull=True)
    )
    for ev in event_qs:
        quill = html_to_quill(ev.comments)
        if not quill:
            continue

        ev.notes = quill
        ev.save(update_fields=['notes'])

        note = Note.objects.create(
            title=f'Notes for: {ev.title}',
            content=quill,
            user_id=ev.user_id,
        )
        NoteLink.objects.create(note=note, event=ev)

    # Migrate Material with details but no NoteLink
    material_qs = (
        Material.objects
        .select_related('material_group')
        .exclude(details='')
        .filter(note_links__isnull=True)
    )
    for mat in material_qs:
        quill = html_to_quill(mat.details)
        if not quill:
            continue

        mat.notes = quill
        mat.save(update_fields=['notes'])

        note = Note.objects.create(
            title=f'Notes for: {mat.title}',
            content=quill,
            user_id=mat.material_group.user_id,
        )
        NoteLink.objects.create(note=note, material=mat)


def migrate_legacy_notes_backward(apps, schema_editor):
    """
    Reverse migration: This is a no-op since we don't want to delete
    Notes that may have been edited by users after migration.

    The legacy `comments`/`details` fields are preserved and unchanged,
    so rolling back simply means the new Note entries remain but aren't
    actively used if the code is also rolled back.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0026_migrate_existing_notes'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_notes_forward, migrate_legacy_notes_backward),
    ]
