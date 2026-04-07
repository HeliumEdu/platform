# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0043_remove_wasteful_indexes'),
    ]

    operations = [
        # Add db_index to updated_at on all models (BaseModel change — queried on every incremental sync)
        migrations.AlterField(
            model_name='attachment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='category',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='course',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='coursegroup',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='courseschedule',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='homework',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='material',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='materialgroup',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='note',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),

        # Reminder: composite index for Celery task queries (sent=False AND type=X AND start_of_range BETWEEN ...)
        migrations.AddIndex(
            model_name='reminder',
            index=models.Index(fields=['sent', 'type', 'start_of_range'], name='reminder_celery_task_lookup'),
        ),

        # Reminder: composite index for API list queries (user scoped, sent/dismissed filters)
        migrations.AddIndex(
            model_name='reminder',
            index=models.Index(fields=['user', 'sent', 'dismissed'], name='reminder_api_list_lookup'),
        ),

        # Homework: composite index for grading aggregation counts (WHERE course_id=X AND completed=Y)
        migrations.AddIndex(
            model_name='homework',
            index=models.Index(fields=['course', 'completed'], name='homework_grading_aggregation'),
        ),
    ]
