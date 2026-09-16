from django.db.models.signals import post_delete
from django.dispatch import receiver

from helium.common.tasks import reconcile_show_getting_started_async
from helium.feed.models import ExternalCalendar


@receiver(post_delete, sender=ExternalCalendar)
def delete_external_calendar(sender, instance, **kwargs):
    reconcile_show_getting_started_async(instance)
