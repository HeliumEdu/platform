__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from django.db import migrations

# Historical values from before 0055_alter_reminder_type shrank REMINDER_TYPE_CHOICES.
# Literal here rather than imported from helium.common.enums, since POPUP/TEXT no longer
# hold their original values there (both now alias PUSH).
POPUP = 0
TEXT = 2
PUSH = 3


def backfill_deprecated_reminder_types(apps, schema_editor):
    """
    Rewrite any Reminder rows still carrying the deprecated POPUP/TEXT type codes to PUSH.

    0055_alter_reminder_type only narrowed the field's `choices` metadata, which Django
    doesn't enforce at the database level, so pre-existing rows kept their raw POPUP/TEXT
    values with nothing normalizing them until now. create_next_repeating_reminder() and
    clone_reminders() both copy `type` verbatim when spawning new reminders, so leaving
    these unconverted would keep propagating the deprecated codes into new rows going
    forward, not just leave stale historical ones behind.

    reminder_one_active_per_course_series (course, user, type, offset, offset_type; active
    only) is a conditional UniqueConstraint, which MySQL doesn't support at the database
    level (Django silently skips creating it there) — so it's only ever been enforced via
    the public API serializer, not against rows created directly by
    create_next_repeating_reminder()/clone_reminders(). A POPUP- or TEXT-typed active
    reminder and a PUSH-typed active reminder can legitimately coexist today for the same
    course/offset/offset_type series (they're different `type` values, so nothing has ever
    flagged them as duplicates). Converting the deprecated one to PUSH in that situation
    would collapse them into an exact duplicate, so those rows are deleted instead of
    updated, matching how create_next_repeating_reminder() already treats same-type
    duplicates for an active series.
    """
    Reminder = apps.get_model('planner', 'Reminder')

    # Safe majority: no active-series collision is possible here, since the constraint
    # only ever applied (even nominally) to active (sent=False, dismissed=False) course
    # reminders.
    safe_updated = Reminder.objects.filter(type__in=[POPUP, TEXT]).exclude(
        course__isnull=False, sent=False, dismissed=False,
    ).update(type=PUSH)

    # Narrow, risky subset: active course reminders, where converting could collide with
    # an already-existing active PUSH reminder for the same series.
    at_risk = Reminder.objects.filter(
        type__in=[POPUP, TEXT], course__isnull=False, sent=False, dismissed=False,
    )

    converted = 0
    deleted_as_duplicate = 0

    for reminder in at_risk:
        collides = Reminder.objects.filter(
            course=reminder.course,
            user=reminder.user,
            type=PUSH,
            offset=reminder.offset,
            offset_type=reminder.offset_type,
            sent=False,
            dismissed=False,
        ).exclude(pk=reminder.pk).exists()

        if collides:
            reminder.delete()
            deleted_as_duplicate += 1
        else:
            # A direct queryset update rather than reminder.save() — this backfill only
            # needs the type column touched, not Reminder.save()'s course-reminder
            # start_of_range recalculation.
            Reminder.objects.filter(pk=reminder.pk).update(type=PUSH)
            converted += 1

    total_updated = safe_updated + converted
    if total_updated > 0 or deleted_as_duplicate > 0:
        print(
            f"\n  Backfilled {total_updated} reminder(s) from deprecated POPUP/TEXT types to "
            f"PUSH ({deleted_as_duplicate} removed as duplicates of an already-active PUSH "
            f"reminder on the same series)"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0057_alter_event_owner_id_alter_material_condition_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_deprecated_reminder_types, migrations.RunPython.noop),
    ]
