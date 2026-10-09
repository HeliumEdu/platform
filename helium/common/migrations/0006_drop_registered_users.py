from django.db import migrations

UNVERIFIED_DELETION = 'verified:false'

VERIFIED_DELETION_PREFIX = 'verified:true,'


def drop_registered_users(apps, schema_editor):
    """
    Cumulative user counts are verified, non-staff users only: drop the registration seed and tally, the
    `registered` milestone, and unverified deletion tallies, and key the remaining deletion tallies by span alone.
    """
    MetricSample = apps.get_model('helium_common', 'MetricSample')

    MetricSample.objects.filter(metric__in=('users.registered.seed', 'users.registered')).delete()
    MetricSample.objects.filter(metric='users.cumulative', dimension='milestone:registered').delete()

    deletions = MetricSample.objects.filter(metric='users.deleted')
    deletions.filter(dimension=UNVERIFIED_DELETION).delete()
    for sample in deletions.filter(dimension__startswith=VERIFIED_DELETION_PREFIX):
        dimension = sample.dimension.removeprefix(VERIFIED_DELETION_PREFIX)
        existing = deletions.filter(recorded_on=sample.recorded_on, dimension=dimension).first()
        if existing:
            existing.value += sample.value
            existing.save(update_fields=['value'])
            sample.delete()
        else:
            sample.dimension = dimension
            sample.save(update_fields=['dimension'])


class Migration(migrations.Migration):

    dependencies = [
        ('helium_common', '0005_seed_registered_users'),
    ]

    operations = [
        migrations.RunPython(drop_registered_users, migrations.RunPython.noop),
    ]
