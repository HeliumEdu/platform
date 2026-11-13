import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dateutil import parser
from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response

from helium.common.serializers.fields import TzAwareDateTimeField
from helium.common.utils import datetimeutils
from helium.common.views.base import HeliumAPIView
from helium.planner.services import recurrenceservice

logger = logging.getLogger(__name__)


CALENDAR_DATE_RANGE_PARAMETERS = [
    OpenApiParameter(
        name='from',
        type=datetime,
        description="Lower bound (inclusive) of the date range filter. Must be provided together with `to`. "
                    "Date-only strings (e.g. `2026-02-02`) are interpreted as midnight in the user's timezone.",
    ),
    OpenApiParameter(
        name='to',
        type=datetime,
        description="Upper bound (inclusive) of the date range filter. Must be provided together with `from`.",
    ),
]


SCOPE_THIS = 'this'
SCOPE_ALL = 'all'

OCCURRENCE_START_PARAMETER = OpenApiParameter(
    name='occurrence_start',
    type=datetime,
    description='The start of the occurrence, exactly as its series expands it.',
)


def scope_parameter(default, description):
    return OpenApiParameter(name='scope', type=str, enum=[SCOPE_THIS, SCOPE_ALL], default=default,
                            description=description)


def recurrence_scope(request, default):
    """
    Return the `scope` query parameter, `this` or `all`, or ``default`` when it is not given.

    :raises ValidationError: if it is anything else
    """
    scope = request.query_params.get('scope', default)
    if scope not in (SCOPE_THIS, SCOPE_ALL):
        raise ValidationError({'scope': f'`scope` must be `{SCOPE_THIS}` or `{SCOPE_ALL}`.'})
    return scope


def occurrence_start_param(request, required):
    """
    Return the `occurrence_start` query parameter as an aware datetime, or None when it is optional and absent.

    :raises ValidationError: if it is required and absent, or is not an aware ISO-8601 datetime
    """
    value = request.query_params.get('occurrence_start')
    if not value:
        if required:
            raise ValidationError({'occurrence_start': '`occurrence_start` is required with this `scope`.'})
        return None
    try:
        return TzAwareDateTimeField().run_validation(value)
    except ValidationError as ex:
        raise ValidationError({'occurrence_start': ex.detail})


def _with_both_occurrence_bounds(instance, occurrence_start, data):
    if ('start' in data) == ('end' in data):
        return data

    start, end = recurrenceservice.find_occurrence(instance, occurrence_start)
    data = data.copy()
    if 'end' in data:
        data['start'] = start.isoformat()
    else:
        try:
            new_start = TzAwareDateTimeField().run_validation(data['start'])
        except ValidationError as ex:
            raise ValidationError({'start': ex.detail})
        tz = ZoneInfo(instance.get_user().settings.time_zone)
        data['end'] = datetimeutils.occurrence_end(start, end, new_start, tz, instance.all_day).isoformat()
    return data


def _parse_date_param_to_utc(date_str, user_tz_name):
    """
    Parse a date/datetime string and convert to UTC.

    When the input is a date-only string (e.g., "2026-02-02"), it's interpreted
    as midnight in the user's timezone, not the server's timezone. This ensures
    consistent filtering regardless of where the server runs.
    """
    dt = parser.parse(date_str)
    if dt.tzinfo is None:
        # Naive datetime - interpret in user's timezone
        dt = dt.replace(tzinfo=ZoneInfo(user_tz_name))
    return dt.astimezone(timezone.utc)


class HeliumCalendarItemAPIView(HeliumAPIView, ListModelMixin):
    def date_range_filter(self, _from, to):
        return (Q(start__range=(_from, to)) |
                Q(end__range=(_from, to)) |
                # Also include results where start/end dates are wider than the window
                Q(start__lte=_from, end__gte=to) |
                Q(start__lte=to, recurrence_rule__isnull=False))

    def filter_queryset(self, queryset):
        _from = self.request.query_params.get('from', None)
        to = self.request.query_params.get('to', None)
        if _from and to:
            user_tz_name = self.request.user.settings.time_zone
            _from = _parse_date_param_to_utc(_from, user_tz_name)
            to = _parse_date_param_to_utc(to, user_tz_name)
            queryset = queryset.filter(self.date_range_filter(_from, to))

        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        return queryset

    def get(self, request, *args, **kwargs):
        _from = request.query_params.get('from')
        to = request.query_params.get('to')

        if (_from and not to) or (to and not _from):
            raise ValidationError(
                detail="Both 'from' and 'to' must be provided together.",
                code=status.HTTP_400_BAD_REQUEST
            )

        return self.list(request, *args, **kwargs)


class RepeatingItemDetailMixin:
    """
    ``scope`` handling for a repeating Event or Homework: ``all`` changes the series, ``this`` changes only the
    occurrence at ``occurrence_start`` by making it its own item first.
    """

    def update_in_scope(self, request, response_serializer_class):
        instance = self.get_object()
        scope = recurrence_scope(request, SCOPE_ALL)
        occurrence_start = occurrence_start_param(request, required=scope == SCOPE_THIS)

        if scope == SCOPE_THIS:
            if 'recurrence_rule' in request.data or 'exception_dates' in request.data:
                raise ValidationError({'scope': 'Change `recurrence_rule` or `exception_dates` with `scope=all`.'})
            with transaction.atomic():
                detached = recurrenceservice.detach_occurrence(instance, occurrence_start)
                serializer = self.get_serializer(detached, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)

            logger.info(f"{type(instance).__name__} {instance.pk} occurrence detached to {detached.pk} for user "
                        f"{request.user.pk}")

            return Response(response_serializer_class(serializer.instance).data)

        data = request.data
        if occurrence_start is not None and instance.recurrence_rule:
            data = _with_both_occurrence_bounds(instance, occurrence_start, data)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        if occurrence_start is not None and instance.recurrence_rule and 'start' in serializer.validated_data:
            serializer.validated_data['start'], serializer.validated_data['end'] = \
                recurrenceservice.series_bounds_for_occurrence_move(instance, occurrence_start,
                                                                    serializer.validated_data['start'],
                                                                    serializer.validated_data['end'])

        self.perform_update(serializer)

        logger.info(f"{type(instance).__name__} {instance.pk} patched for user {request.user.pk}")

        return Response(response_serializer_class(serializer.instance).data)

    def destroy_in_scope(self, request, *args, **kwargs):
        if recurrence_scope(request, SCOPE_ALL) == SCOPE_THIS:
            instance = self.get_object()
            recurrenceservice.exclude_occurrence(instance, occurrence_start_param(request, required=True))
            logger.info(f"{type(instance).__name__} {instance.pk} occurrence deleted for user {request.user.pk}")
            return Response(status=status.HTTP_204_NO_CONTENT)

        response = self.destroy(request, *args, **kwargs)

        logger.info(f"{self.get_queryset().model.__name__} {kwargs['pk']} deleted for user {request.user.pk}")

        return response

