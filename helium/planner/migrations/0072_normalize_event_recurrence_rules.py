import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import migrations

from helium.common.utils.validators import prepare_recurrence_rule

logger = logging.getLogger(__name__)


def normalize_event_recurrence_rules(apps, schema_editor):
    """
    Rewrite stored rules into the subset SfCalendar expands, and drop the rules it cannot expand.

    Rules saved before monthly and yearly shapes were normalized and validated can throw while the client
    expands them, which breaks the whole calendar. A dropped rule leaves its event as a single occurrence, as
    an unsupported rule in a feed already does.
    """
    Event = apps.get_model('planner', 'Event')

    normalized_count = 0
    dropped_count = 0
    for pk, recurrence_rule, start, time_zone in (Event.objects
                                                  .exclude(recurrence_rule__isnull=True)
                                                  .exclude(recurrence_rule='')
                                                  .order_by('pk')
                                                  .values_list('pk', 'recurrence_rule', 'start',
                                                               'user__settings__time_zone')
                                                  .iterator(chunk_size=2000)):
        try:
            normalized = prepare_recurrence_rule(recurrence_rule, start.astimezone(ZoneInfo(time_zone)))
        except ValidationError:
            logger.info(f'Dropping unsupported recurrence rule from event {pk}: {recurrence_rule}')
            normalized = None
            dropped_count += 1
        else:
            if normalized != recurrence_rule:
                normalized_count += 1

        if normalized != recurrence_rule:
            Event.objects.filter(pk=pk).update(recurrence_rule=normalized)

    logger.info(f'{normalized_count} recurrence rule(s) normalized, {dropped_count} dropped.')


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0071_alter_homework_current_grade_help_text'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(normalize_event_recurrence_rules, migrations.RunPython.noop),
    ]
