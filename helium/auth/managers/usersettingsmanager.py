import logging

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class UserSettingsQuerySet(models.query.QuerySet):
    def eligible_for_review_prompt(self):
        return self.filter(user__is_active=True,
                           prompt_for_review=False,
                           next_review_prompt_date__isnull=False,
                           next_review_prompt_date__lte=timezone.now(),
                           review_prompts_requested__lt=settings.REVIEW_PROMPT_MAX_REQUESTED)


class UserSettingsManager(models.Manager):
    def get_queryset(self):
        return UserSettingsQuerySet(self.model, using=self._db)

    def eligible_for_review_prompt(self):
        return self.get_queryset().eligible_for_review_prompt()
