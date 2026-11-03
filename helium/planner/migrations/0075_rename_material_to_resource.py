import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0074_remove_comments_and_details'),
        ('helium_auth', '0077_backfill_example_schedule_imported_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(old_name='MaterialGroup', new_name='ResourceGroup'),
        migrations.RenameModel(old_name='Material', new_name='Resource'),
        migrations.RenameField(model_name='resource', old_name='material_group', new_name='resource_group'),
        migrations.RenameField(model_name='homework', old_name='materials', new_name='resources'),
        migrations.AlterField(
            model_name='resource',
            name='courses',
            field=models.ManyToManyField(blank=True, default=None,
                                         help_text='Classes that share this resource. May be empty.',
                                         related_name='resources', to='planner.course'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='resource_group',
            field=models.ForeignKey(help_text='The resource group with which to associate.',
                                    on_delete=django.db.models.deletion.CASCADE, related_name='resources',
                                    to='planner.resourcegroup'),
        ),
        migrations.AlterField(
            model_name='resourcegroup',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resource_groups',
                                    to=settings.AUTH_USER_MODEL),
        ),
    ]
