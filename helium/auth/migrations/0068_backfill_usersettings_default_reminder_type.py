__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from django.db import migrations

# Literals, not imported from helium.common.enums: POPUP/TEXT were removed there and no
# longer hold their original values (both now alias PUSH).
POPUP = 0
TEXT = 2
PUSH = 3


def backfill_usersettings_default_reminder_type(apps, schema_editor):
    """
    Normalize UserSettings.default_reminder_type off the deprecated POPUP/TEXT codes.

    planner/0058 and planner/0064 backfilled Reminder.type, but the parallel
    UserSettings.default_reminder_type column was only ever narrowed via AlterField
    (0065_alter_usersettings_default_reminder_type), which changes `choices` metadata
    only and isn't enforced at the database level. Accounts that had selected Popup or
    Text as their default still carry those raw codes, so clients crash resolving the
    value to a dropdown item when seeding the preferences screen and the new-reminder
    dialog. Sweep them to PUSH, the field's own default.
    """
    UserSettings = apps.get_model('helium_auth', 'UserSettings')

    updated = UserSettings.objects.filter(
        default_reminder_type__in=[POPUP, TEXT],
    ).update(default_reminder_type=PUSH)

    if updated > 0:
        print(
            f"\n  Backfilled {updated} UserSettings row(s) from deprecated POPUP/TEXT "
            f"default_reminder_type to PUSH"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0067_alter_user_username_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_usersettings_default_reminder_type, migrations.RunPython.noop),
    ]
