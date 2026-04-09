from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helium_common', '0001_initial'),
        ('django_celery_results', '0014_alter_taskresult_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskResultProxy',
            fields=[],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('django_celery_results.taskresult',),
        ),
    ]
