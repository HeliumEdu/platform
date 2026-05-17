__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime

from rest_framework import serializers


class ExceptionDatesField(serializers.ListField):
    """
    Serializer field for the planner ``Event.exception_dates`` JSONField column.
    Wraps a :class:`TzAwareDateTimeField` so per-item parsing, validation, and
    output formatting all flow through the same DRF DateTimeField machinery as
    every other datetime in the API — meaning the wire form is uniformly
    ``Z``-suffixed ISO-8601 UTC regardless of whether the column was populated
    by user POST, iCal import, or anything else.

    Without this, JSON-stored strings would pass through DRF as-is and the wire
    format would drift away from the rest of the API's datetime convention.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('child', TzAwareDateTimeField(default_timezone=datetime.timezone.utc))
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        # DRF's ListField parses each entry to a datetime via the child field.
        # Convert back to ISO strings here so the JSONField column stores plain
        # JSON (Python's default encoder can't serialize datetimes) — using
        # DateTimeField's own ``to_representation`` so the Z-suffix normalization
        # happens at the same place for both write and read paths.
        datetimes = super().to_internal_value(data)
        if datetimes is None:
            return None
        return [self.child.to_representation(dt) for dt in datetimes]

    def to_representation(self, data):
        if data is None:
            return data
        # Stored values are already Z-suffixed ISO strings (written by
        # ``to_internal_value`` for user input, or by the iCal import service
        # which writes any ISO form). Parse and re-emit through DateTimeField
        # so legacy ``+00:00``-form values still come out as ``Z`` on the wire.
        normalized = []
        for value in data:
            if isinstance(value, str):
                value = datetime.datetime.fromisoformat(value)
            normalized.append(self.child.to_representation(value))
        return normalized


class TzAwareDateTimeField(serializers.DateTimeField):
    """
    A :class:`~rest_framework.serializers.DateTimeField` that rejects naive
    (timezone-unaware) inputs with a 400 instead of silently re-casting them
    to UTC. Naive datetimes are the most common syllabus-import bug: a
    Pacific-time student writes `"2026-10-14T09:55:00"` and the assignment
    lands at 2:55 AM PT on their calendar.

    Aware inputs (offset like ``-07:00`` or the ``Z`` UTC suffix) pass
    through unchanged.
    """

    def to_internal_value(self, value):
        if isinstance(value, str):
            parsed = self._try_parse(value)
            if parsed is not None and parsed.tzinfo is None:
                self.fail('naive_datetime')
        elif isinstance(value, datetime.datetime) and value.tzinfo is None:
            self.fail('naive_datetime')
        return super().to_internal_value(value)

    default_error_messages = {
        **serializers.DateTimeField.default_error_messages,
        'naive_datetime': (
            'Datetime must include a timezone (e.g. `-07:00` offset or `Z` for UTC).'
        ),
    }

    def _try_parse(self, value):
        """
        Best-effort parse of an ISO 8601 string so we can inspect its tzinfo
        before DRF's normal parsing runs. Returns ``None`` if the string is
        not parseable; the parent class will then surface its standard
        format error.
        """
        # Accept both `Z` and `+00:00` style suffixes — `fromisoformat`
        # gained `Z` support in 3.11, and the codebase pins newer Python.
        try:
            return datetime.datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
