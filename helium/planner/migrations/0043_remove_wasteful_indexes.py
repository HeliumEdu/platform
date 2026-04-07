# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0042_reminder_dismissed_requires_sent'),
    ]

    operations = [
        # Remove db_index from created_at on all models (BaseModel change — no longer queried)
        migrations.AlterField(
            model_name='attachment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='category',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='course',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='coursegroup',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='courseschedule',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='homework',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='material',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='materialgroup',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='note',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),

        # Remove db_index from title on all models (ordering-only; new frontend filters client-side)
        migrations.AlterField(
            model_name='attachment',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='category',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='course',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='coursegroup',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='event',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='homework',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='material',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='materialgroup',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='note',
            name='title',
            field=models.CharField(blank=True, help_text='Display title for the note.', max_length=255),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='title',
            field=models.CharField(help_text='A display name.', max_length=255),
        ),

        # Remove db_index from CourseGroup date fields and shown_on_calendar (legacy FilterSet only)
        migrations.AlterField(
            model_name='coursegroup',
            name='start_date',
            field=models.DateField(help_text='An ISO-8601 date.'),
        ),
        migrations.AlterField(
            model_name='coursegroup',
            name='end_date',
            field=models.DateField(help_text='An ISO-8601 date.'),
        ),
        migrations.AlterField(
            model_name='coursegroup',
            name='shown_on_calendar',
            field=models.BooleanField(default=True, help_text='Whether items should be shown on the calendar.'),
        ),

        # Remove db_index from Course date fields (legacy FilterSet only)
        migrations.AlterField(
            model_name='course',
            name='start_date',
            field=models.DateField(help_text='An ISO-8601 date.'),
        ),
        migrations.AlterField(
            model_name='course',
            name='end_date',
            field=models.DateField(help_text='An ISO-8601 date.'),
        ),

        # Remove db_index from Reminder status/type fields (superseded by composites in next migration)
        migrations.AlterField(
            model_name='reminder',
            name='type',
            field=models.PositiveIntegerField(
                choices=[(0, 'Popup'), (1, 'Email'), (2, 'Text'), (3, 'Push')],
                default=0,
                help_text='A valid reminder type choice.',
            ),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='sent',
            field=models.BooleanField(default=False, help_text='Whether the reminder has been sent.'),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='dismissed',
            field=models.BooleanField(default=False, help_text='Whether the reminder has been dismissed.'),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='start_of_range',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
