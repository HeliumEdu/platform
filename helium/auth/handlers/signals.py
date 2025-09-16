from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def post_save_user(sender, instance, created, **kwargs):
    """
    After a user is created, one-to-one references to profile and settings models must be created to finish
    provisioning the new user.
    """
    if created:
        get_user_model().objects.create_references(instance)
