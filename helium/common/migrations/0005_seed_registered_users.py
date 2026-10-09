from django.db import migrations
from django.db.models import Max
from django.utils import timezone


def seed_registered_users(apps, schema_editor):
    """
    Seed cumulative registrations with the highest user ID issued so far. IDs count every account ever created,
    staff included, since staff can't be told apart once deleted; registrations after this point are tallied
    only for non-staff accounts.
    """
    User = apps.get_model('helium_auth', 'User')
    MetricSample = apps.get_model('helium_common', 'MetricSample')

    highest_user_id = User.objects.aggregate(highest=Max('pk'))['highest'] or 0
    MetricSample.objects.get_or_create(metric='users.registered.seed', dimension='',
                                       defaults={'recorded_on': timezone.now().date(), 'value': highest_user_id})


class Migration(migrations.Migration):

    dependencies = [
        ('helium_common', '0004_metricsample'),
        ('helium_auth', '0077_backfill_example_schedule_imported_at'),
    ]

    operations = [
        migrations.RunPython(seed_registered_users, migrations.RunPython.noop),
    ]
