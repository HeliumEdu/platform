from functools import partial

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from helium.common.services import cumulativeuserservice


@receiver(post_save, sender=get_user_model())
def post_save_user(sender, instance, created, **kwargs):
    """
    After a user is created, one-to-one references to profile and settings models must be created to finish
    provisioning the new user, and the account is counted toward cumulative registrations once committed.
    """
    if created:
        get_user_model().objects.create_references(instance)

        transaction.on_commit(partial(cumulativeuserservice.record_registered_user, instance))
