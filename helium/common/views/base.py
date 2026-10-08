import logging
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView

from helium.common.utils import metricutils
from helium.common.utils.commonutils import PreconditionFailedError

logger = logging.getLogger(__name__)

CONDITIONAL_METHODS = ('PUT', 'PATCH', 'DELETE')

IF_MATCH_PARAMETER = OpenApiParameter(
    name='If-Match',
    location=OpenApiParameter.HEADER,
    required=False,
    description="The item's `updated_at` as last read. If the item has changed since, returns 412 with the current "
                "item. Omit to write unconditionally.",
)


class HeliumAPIView(GenericAPIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__request_metrics = None

    def has_request_user(self):
        """
        Whether this is a real request with a `user`, as opposed to drf-spectacular's schema generation
        (`swagger_fake_view`), where querysets must stay empty.
        """
        return hasattr(self.request, 'user') and not getattr(self, 'swagger_fake_view', False)

    def initial(self, request, *args, **kwargs):
        self.__request_metrics = metricutils.request_start(request)

        super().initial(request, *args, **kwargs)

        if settings.SENTRY_ENABLED and request.user and request.user.is_authenticated:
            import sentry_sdk
            sentry_sdk.set_user({"id": request.user.id})

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if self.__request_metrics:
            metricutils.request_stop(self.__request_metrics, request, response,
                                     searchable=bool(getattr(self, 'search_fields', None)))

        if request.user and request.user.is_authenticated:
            metricutils.record_presence(request.user)

        return response


class PreconditionMixin:
    """
    Optimistic concurrency for detail views. A PUT, PATCH or DELETE that sends `If-Match` with the item's
    `updated_at` only proceeds if the item is still at that version; otherwise it fails with 412 and the current item
    in the body. The check and the write share a transaction with the row locked, so two writes from the same version
    cannot both succeed. Without the header the request behaves as it always has.
    """

    #: The serializer for the current item in a 412 body; defaults to the view's serializer.
    precondition_serializer_class = None

    def dispatch(self, request, *args, **kwargs):
        if request.method in CONDITIONAL_METHODS and request.headers.get('If-Match'):
            with transaction.atomic():
                return super().dispatch(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        obj = super().get_object()

        if_match = self.request.headers.get('If-Match') if self.request.method in CONDITIONAL_METHODS else None
        if not if_match or if_match.strip() == '*':
            return obj

        expected = _parse_if_match(if_match)
        current = (type(obj).objects.select_for_update()
                   .filter(pk=obj.pk)
                   .values_list('updated_at', flat=True)
                   .first())
        if current != obj.updated_at:
            obj = super().get_object()

        if current != expected:
            logger.info(
                f'{type(obj).__name__} {obj.pk} failed its If-Match precondition for user {self.request.user.pk}')

            serializer_class = self.precondition_serializer_class or self.get_serializer_class()
            raise PreconditionFailedError(serializer_class(obj, context=self.get_serializer_context()).data)

        return obj


def _parse_if_match(value: str) -> datetime:
    tag = value.strip()
    if tag.startswith('W/'):
        tag = tag[2:]
    parsed = parse_datetime(tag.strip('"'))
    if parsed is None:
        raise ValidationError({'If-Match': ['The If-Match header must be the updated_at of the item being changed.']})

    return timezone.make_aware(parsed, dt_timezone.utc) if timezone.is_naive(parsed) else parsed
