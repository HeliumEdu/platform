from django.db import migrations
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Max
from django.utils import timezone


def restore_total_users_seed(apps, schema_editor):
    """
    Restore the total-users seed removed by 0006: the highest ID among users created by the time 0005 first seeded
    it, so the restored value matches the original apart from accounts deleted since.
    """
    MetricSample = apps.get_model('helium_common', 'MetricSample')
    User = apps.get_model('helium_auth', 'User')

    if MetricSample.objects.filter(metric='users.registered.seed').exists():
        return

    seeded_at = MigrationRecorder(schema_editor.connection).migration_qs.filter(
        app='helium_common', name='0005_seed_registered_users').values_list('applied', flat=True).first()
    users = User.objects.filter(created_at__lte=seeded_at) if seeded_at else User.objects.all()

    MetricSample.objects.create(metric='users.registered.seed', dimension='',
                                recorded_on=(seeded_at or timezone.now()).date(),
                                value=users.aggregate(highest=Max('pk'))['highest'] or 0)


class Migration(migrations.Migration):

    dependencies = [
        ('helium_common', '0006_drop_registered_users'),
        ('helium_auth', '0077_backfill_example_schedule_imported_at'),
    ]

    operations = [
        migrations.RunPython(restore_total_users_seed, migrations.RunPython.noop),
    ]
