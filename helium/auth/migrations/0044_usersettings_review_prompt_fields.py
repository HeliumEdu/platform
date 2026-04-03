# Generated manually

from datetime import timedelta

from django.db import migrations, models


def seed_next_review_prompt_date(apps, schema_editor):
    UserSettings = apps.get_model('helium_auth', 'UserSettings')

    to_update = []
    for user_settings in UserSettings.objects.select_related('user').filter(user__is_active=True):
        user_settings.next_review_prompt_date = user_settings.user.date_joined + timedelta(days=21)
        to_update.append(user_settings)

    UserSettings.objects.bulk_update(to_update, ['next_review_prompt_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0043_usersettings_on_track_tolerance_show_week_numbers'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='prompt_for_review',
            field=models.BooleanField(
                default=False,
                help_text='Whether the user should be prompted to review the app on their next eligible mobile session.',
            ),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='next_review_prompt_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='The earliest date/time the user is eligible to be prompted to review the app. Null until first login.',
            ),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='review_prompts_shown',
            field=models.PositiveIntegerField(
                default=0,
                help_text='The number of times the user has been shown the app review prompt.',
            ),
        ),
        migrations.RunPython(seed_next_review_prompt_date, migrations.RunPython.noop),
    ]
