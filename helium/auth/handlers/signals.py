from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from oauth2_provider.signals import app_authorized

from helium.auth.services import oauthservice


@receiver(post_save, sender=get_user_model())
def post_save_user(sender, instance, created, **kwargs):
    """
    After a user is created, one-to-one references to profile and settings models must be created to finish
    provisioning the new user.
    """
    if created:
        get_user_model().objects.create_references(instance)


@receiver(app_authorized)
def oauth_token_issued(sender, request, token, **kwargs):
    """
    After a connector is issued an OAuth token (or refreshes one), count it as the user's activity.
    """
    oauthservice.record_token_issued(token, request)
