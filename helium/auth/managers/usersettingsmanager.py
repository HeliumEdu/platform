import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from helium.auth.models.userclientactivity import UserClientActivity

logger = logging.getLogger(__name__)


class UserSettingsQuerySet(models.query.QuerySet):
    def eligible_for_review_prompt(self):
        has_mobile_activity = Exists(UserClientActivity.objects.filter(user_id=OuterRef('user_id'),
                                                                       client=UserClientActivity.CLIENT_MOBILE_APP))

        return self.filter(has_mobile_activity,
                           user__is_active=True,
                           prompt_for_review=False,
                           next_review_prompt_date__isnull=False,
                           next_review_prompt_date__lte=timezone.now(),
                           review_prompts_requested__lt=settings.REVIEW_PROMPT_MAX_REQUESTED) \
                   .exclude(user__in=get_user_model().objects.staff())


class UserSettingsManager(models.Manager):
    def get_queryset(self):
        return UserSettingsQuerySet(self.model, using=self._db)

    def eligible_for_review_prompt(self):
        return self.get_queryset().eligible_for_review_prompt()

    def language_for_email(self, email):
        language = (self.get_queryset().filter(Q(user__email=email) | Q(user__email_changing=email))
                    .values_list('language', flat=True).first())
        return language or self.model._meta.get_field('language').default
