__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json

from django.db import migrations


def fix_list_newline_forward(apps, schema_editor):
    """
    Fix notes where text before a list was incorrectly concatenated with
    the first list item (missing newline separator).

    The buggy pattern is:
      op[i]: text not ending in newline
      op[i+1]: text not ending in newline
      op[i+2]: newline with list attribute

    This indicates op[i] was meant to be a separate paragraph but got
    concatenated with the list item in op[i+1].
    """
    Note = apps.get_model('planner', 'Note')

    fixed_count = 0
    for note in Note.objects.exclude(content__isnull=True).iterator():
        content = note.content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                continue

        ops = content.get('ops', [])
        if not ops:
            continue

        fixed_ops, num_fixes = _fix_buggy_pattern(ops)
        if num_fixes > 0:
            content['ops'] = fixed_ops
            note.content = content
            note.save(update_fields=['content'])
            fixed_count += 1

    if fixed_count:
        print(f"  Fixed {fixed_count} notes with missing list newlines")


def _fix_buggy_pattern(ops):
    """
    Fix the buggy pattern by inserting a newline between the intro text
    and the list item text.

    Returns (fixed_ops, num_fixes)
    """
    fixed_ops = []
    fixes = 0
    i = 0

    while i < len(ops):
        op = ops[i]
        fixed_ops.append(op)

        # Check if this starts a buggy pattern
        if i + 2 < len(ops):
            op2 = ops[i + 1]
            op3 = ops[i + 2]

            insert1 = op.get('insert', '')
            insert2 = op2.get('insert', '')
            insert3 = op3.get('insert', '')

            is_buggy = (
                isinstance(insert1, str) and not insert1.endswith('\n') and insert1 != '\n' and
                isinstance(insert2, str) and not insert2.endswith('\n') and insert2 != '\n' and
                insert3 == '\n' and 'list' in op3.get('attributes', {})
            )

            if is_buggy:
                # Insert a newline to separate intro from list
                fixed_ops.append({'insert': '\n'})
                fixes += 1

        i += 1

    return fixed_ops, fixes


def fix_list_newline_backward(apps, schema_editor):
    """Reverse migration is not feasible - the fix is additive and safe."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0030_rename_notelink_material_to_resource'),
    ]

    operations = [
        migrations.RunPython(fix_list_newline_forward, fix_list_newline_backward),
    ]
