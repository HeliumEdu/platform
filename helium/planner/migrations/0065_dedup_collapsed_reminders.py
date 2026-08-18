from django.db import migrations


def dedup_collapsed_reminders(apps, schema_editor):
    """Remove reminders duplicated by the Popup/Text to Push merge.

    0058/0064 converted deprecated Popup(0)/Text(2) codes to Push(3) but only deduped active
    course reminders, so users who had two of Popup/Text/Push at the same offset on the same
    assignment or event (or a sent/dismissed course reminder) were left with identical rows.

    Key includes title/message so only truly-identical rows collapse. Ordering keeps an
    unsent, undismissed row first (lowest pk tiebreak); the rest are deleted.
    """
    Reminder = apps.get_model('planner', 'Reminder')

    seen = set()
    to_delete = []
    for r in Reminder.objects.order_by('sent', 'dismissed', 'pk').iterator():
        key = (r.user_id, r.homework_id, r.event_id, r.course_id,
               r.offset, r.offset_type, r.type, r.title, r.message)
        if key in seen:
            to_delete.append(r.pk)
        else:
            seen.add(key)

    if to_delete:
        Reminder.objects.filter(pk__in=to_delete).delete()
        print(f"\n  Removed {len(to_delete)} reminder(s) duplicated by the Popup/Text to Push merge")


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0064_backfill_remaining_reminder_types'),
    ]

    operations = [
        migrations.RunPython(dedup_collapsed_reminders, migrations.RunPython.noop),
    ]
