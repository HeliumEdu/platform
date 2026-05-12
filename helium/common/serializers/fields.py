__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime

from rest_framework import serializers


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
