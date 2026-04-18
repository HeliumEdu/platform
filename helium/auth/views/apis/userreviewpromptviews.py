__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


class UserReviewPromptAckView(HeliumAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Acknowledge that the review prompt has been shown to the authenticated user. Clears the
        prompt flag, increments the shown count, and sets a cooldown before the user is eligible
        to be prompted again.
        """
        user_settings = request.user.settings

        user_settings.prompt_for_review = False
        user_settings.review_prompts_requested += 1
        user_settings.next_review_prompt_date = timezone.now() + timedelta(days=settings.REVIEW_PROMPT_COOLDOWN_DAYS)
        user_settings.save(update_fields=['prompt_for_review', 'review_prompts_requested', 'next_review_prompt_date'])

        logger.info(
            f'User {request.user.pk} acknowledged review prompt (shown {user_settings.review_prompts_requested} time(s))')

        return Response(status=status.HTTP_204_NO_CONTENT)
