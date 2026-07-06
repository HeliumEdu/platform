__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import decimal
import re
import sys

from dateutil.rrule import rrulestr
from django.core.exceptions import ValidationError

from helium.common.utils import commonutils

# Reference dtstart used solely to satisfy rrulestr() during validation. The actual
# series anchor at runtime is the parent Event's `start`, not this constant.
_RRULE_VALIDATION_DTSTART = datetime.datetime(2000, 1, 1)

_WEEKDAY_TO_ICAL = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR', 5: 'SA', 6: 'SU'}


def validate_fraction(value):
    """
    Ensure the given value is a valid fraction (1235/2346) with valid numbers on either side of the ratio. If not,
    raise a validation error.
    """
    split = value.split('/')
    if len(split) != 2:
        raise ValidationError('Enter a valid fraction of the format \'x/y\'.')

    try:
        n = decimal.Decimal(split[0].strip())
        d = decimal.Decimal(split[1].strip())
    except (ValueError, decimal.InvalidOperation):
        raise ValidationError('The fraction must contain valid integers.')

    if n > sys.maxsize or d > sys.maxsize:
        raise ValidationError(f'Values must be less than or equal to {sys.maxsize}.')

    if d <= 0:
        raise ValidationError('The denominator must be greater than zero.')

    return f'{commonutils.remove_exponent(n.normalize())}/{commonutils.remove_exponent(d.normalize())}'


def validate_hex_color(value):
    if not re.match(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$', value):
        raise ValidationError('The value must be a valid hex color code.')


def validate_quill_delta(value):
    """
    Outer-shape check for Quill Delta JSON content: ``None``, ``{}`` (the
    wire-level clear-content signal), or a dict with an ``ops`` list. Per-op
    shape and attribute correctness are left to the client renderer
    (`flutter_quill`'s ``Document.fromJson``).
    """
    if value is None or value == {}:
        return
    if not isinstance(value, dict):
        raise ValidationError('Quill content must be an object.')
    if not isinstance(value.get('ops'), list):
        raise ValidationError('Quill content must have an `ops` list.')


def infer_byday_for_weekly_rrule(value, dtstart):
    """
    RFC 5545 allows ``FREQ=WEEKLY`` without ``BYDAY``, implying recurrence on
    the same weekday as ``DTSTART``. SfCalendar requires ``BYDAY`` explicitly.
    If ``value`` is a weekly RRULE without ``BYDAY``, this function infers it
    from ``dtstart`` and returns the augmented string. All other RRULEs are
    returned unchanged.
    """
    if not value:
        return value

    prefix = ''
    rule_body = value
    if value.upper().startswith('RRULE:'):
        prefix = value[:6]
        rule_body = value[6:]

    parts = {}
    for part in rule_body.split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            parts[k.upper()] = v

    if parts.get('FREQ') != 'WEEKLY' or 'BYDAY' in parts:
        return value

    day_code = _WEEKDAY_TO_ICAL[dtstart.weekday()]
    return f'{prefix}{rule_body};BYDAY={day_code}'


_UNSUPPORTED_RRULE_FREQS = frozenset({'HOURLY', 'MINUTELY', 'SECONDLY'})
_UNSUPPORTED_RRULE_PARTS = frozenset({'BYWEEKNO', 'BYYEARDAY', 'WKST'})


def validate_recurrence_rule(value):
    """
    Validate that ``value`` is a parseable RFC 5545 RRULE string (e.g. ``FREQ=WEEKLY;BYDAY=MO``).

    Accepts both bare rule bodies and the ``RRULE:`` prefixed form. A reference dtstart is
    supplied to ``rrulestr`` only to satisfy parsing — the real series anchor is the parent
    Event's ``start``.

    Rejects properties that are valid per RFC 5545 but not rendered correctly by SfCalendar:
    FREQ=HOURLY/MINUTELY/SECONDLY (silently produces no instances), BYWEEKNO and BYYEARDAY
    (silently ignored → wrong dates), and WKST (silently ignored → wrong week boundaries).
    """
    if value is None or value == '':
        return

    rule_body = value[6:] if value.upper().startswith('RRULE:') else value
    parts = {}
    for part in rule_body.split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            parts[k.upper()] = v.upper()

    freq = parts.get('FREQ', '')
    if freq in _UNSUPPORTED_RRULE_FREQS:
        raise ValidationError(f'FREQ={freq} is not supported.')

    for key in _UNSUPPORTED_RRULE_PARTS:
        if key in parts:
            raise ValidationError(f'{key} is not supported.')

    try:
        rrulestr(value, dtstart=_RRULE_VALIDATION_DTSTART)
    except (ValueError, TypeError) as ex:
        raise ValidationError(f'Invalid RRULE: {ex}')


def validate_and_normalize_date_csv(value, start_date=None, end_date=None, range_label='date range'):
    """
    Validate that ``value`` is a CSV of YYYYMMDD-formatted dates.  Optionally checks each date falls within
    [``start_date``, ``end_date``].  Returns a deduplicated, sorted, normalized CSV string.

    :param value: raw comma-separated string
    :param start_date: inclusive lower bound (optional)
    :param end_date: inclusive upper bound (optional)
    :param range_label: human-readable label used in the out-of-range error message
    :raises ValidationError: on any invalid token or out-of-range date
    """
    seen = set()
    deduped = []
    for token in value.split(','):
        token = token.strip()
        if not token:
            continue
        try:
            date = datetime.datetime.strptime(token, '%Y%m%d').date()
        except ValueError:
            raise ValidationError(f'Invalid date format: {token}')
        if start_date and end_date and not (start_date <= date <= end_date):
            raise ValidationError(f'Exception dates must fall within the {range_label}.')
        if date not in seen:
            seen.add(date)
            deduped.append(date)
    return ','.join(d.strftime('%Y%m%d') for d in sorted(deduped))
