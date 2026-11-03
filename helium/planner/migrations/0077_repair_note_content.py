import logging

from django.db import migrations

from helium.common.utils.validators import is_quill_document_op

logger = logging.getLogger(__name__)


def repair_note_content(apps, schema_editor):
    """
    Drop the ops that don't belong in a document (``retain``, ``delete``, malformed entries) from stored notes, which
    no client can render. Every character of a note's text is an ``insert``, so the text survives; at most formatting
    an edit op described is lost. A note left with nothing becomes an empty document.
    """
    Note = apps.get_model('planner', 'Note')

    repaired = 0
    for note in Note.objects.exclude(content=None).only('id', 'content').iterator():
        ops = (note.content or {}).get('ops')
        if not isinstance(ops, list) or all(is_quill_document_op(op) for op in ops):
            continue
        kept = [op for op in ops if is_quill_document_op(op)] or [{'insert': '\n'}]
        Note.objects.filter(pk=note.pk).update(content={'ops': kept})
        repaired += 1

    logger.info(f'Repaired the content of {repaired} note(s) holding non-document ops')


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0076_recalculate_weighted_grades'),
    ]

    operations = [
        migrations.RunPython(repair_note_content, migrations.RunPython.noop),
    ]
