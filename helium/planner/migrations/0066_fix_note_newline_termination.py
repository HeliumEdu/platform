__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import json

from django.db import migrations


def _is_terminated(ops):
    if not ops:
        return False
    last = ops[-1]
    insert = last.get('insert') if isinstance(last, dict) else None
    return isinstance(insert, str) and insert.endswith('\n')


def fix_note_newline_termination_forward(apps, schema_editor):
    """Ensure every note's content ends in a newline.

    Legacy notes migrated verbatim by 0026 were never guaranteed to be
    newline-terminated, which Quill requires. An un-terminated delta renders a
    child-less document that crashes flutter_quill's hit-testing on the first
    tap. Appending the missing newline makes those notes renderable.
    """
    Note = apps.get_model('planner', 'Note')

    fixed_count = 0
    for note in Note.objects.exclude(content__isnull=True).iterator():
        content = note.content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (ValueError, TypeError):
                continue

        if not isinstance(content, dict):
            continue

        ops = content.get('ops')
        if not isinstance(ops, list) or not ops or _is_terminated(ops):
            continue

        content['ops'] = [*ops, {'insert': '\n'}]
        note.content = content
        note.save(update_fields=['content'])
        fixed_count += 1

    if fixed_count:
        print(f"  Fixed {fixed_count} notes missing trailing newline")


def fix_note_newline_termination_backward(apps, schema_editor):
    """Reverse migration is not feasible - the fix is additive and safe."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0065_dedup_collapsed_reminders'),
    ]

    operations = [
        migrations.RunPython(fix_note_newline_termination_forward, fix_note_newline_termination_backward),
    ]
