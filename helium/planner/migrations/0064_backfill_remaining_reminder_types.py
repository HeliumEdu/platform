from django.db import migrations

# Literals, not enums: POPUP/TEXT were removed from helium.common.enums.
POPUP = 0
TEXT = 2
PUSH = 3


def backfill_remaining_reminder_types(apps, schema_editor):
    """Convert any lingering POPUP/TEXT reminders to PUSH.

    Follow-up to 0058: example_schedule.json still carried type=0 and the example
    importer saves it unvalidated, so imports after 0058 re-minted POPUP rows. The
    JSON is now fixed; this sweeps up the strays.
    """
    Reminder = apps.get_model('planner', 'Reminder')

    # Non-active-course reminders convert freely.
    converted = Reminder.objects.filter(type__in=[POPUP, TEXT]).exclude(
        course__isnull=False, sent=False, dismissed=False,
    ).update(type=PUSH)

    # Active course reminders may collide with an existing active PUSH reminder on the
    # same series (which the API forbids) — delete those rather than convert.
    deleted = 0
    for reminder in Reminder.objects.filter(
        type__in=[POPUP, TEXT], course__isnull=False, sent=False, dismissed=False,
    ):
        collides = Reminder.objects.filter(
            course=reminder.course, user=reminder.user, type=PUSH,
            offset=reminder.offset, offset_type=reminder.offset_type,
            sent=False, dismissed=False,
        ).exclude(pk=reminder.pk).exists()

        if collides:
            reminder.delete()
            deleted += 1
        else:
            Reminder.objects.filter(pk=reminder.pk).update(type=PUSH)
            converted += 1

    if converted or deleted:
        print(f"\n  Backfilled {converted} POPUP/TEXT reminder(s) to PUSH "
              f"({deleted} removed as active-series duplicates)")


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0063_alter_reminder_event'),
    ]

    operations = [
        migrations.RunPython(backfill_remaining_reminder_types, migrations.RunPython.noop),
    ]
