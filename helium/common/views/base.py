__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.db import transaction
from rest_framework.generics import GenericAPIView

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class SafeDestroyMixin:
    """Serialize concurrent deletes to prevent cascade check-constraint violations.

    Wraps ``perform_destroy`` in ``transaction.atomic()`` with
    ``select_for_update()`` so that concurrent DELETE requests for the same
    row are serialized at the database level.  If the row has already been
    deleted by another thread, the method returns silently (the caller still
    gets 204).

    Apply to any detail view whose cascade path passes through a SET_NULL FK
    into a table protected by a CHECK constraint (e.g. CourseGroup → Course →
    Category → Homework.category SET_NULL, while Attachment/Reminder enforce
    ``exactly_one_parent``).
    """

    def perform_destroy(self, instance):
        with transaction.atomic():
            locked = (
                type(instance)
                .objects.select_for_update()
                .filter(pk=instance.pk)
                .first()
            )
            if locked is None:
                return
            locked.delete()


class HeliumAPIView(GenericAPIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__request_metrics = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if settings.SENTRY_ENABLED and request.user and request.user.is_authenticated:
            import sentry_sdk
            sentry_sdk.set_user({"id": request.user.id})

        self.__request_metrics = metricutils.request_start(request)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if self.__request_metrics:
            metricutils.request_stop(self.__request_metrics, request, response)

        return response
