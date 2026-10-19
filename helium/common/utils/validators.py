import datetime
import decimal
import re
import sys
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from django.core.exceptions import ValidationError

from helium.common.utils import commonutils

# Reference dtstart used solely to satisfy rrulestr() during validation. The actual
# series anchor at runtime is the parent Event's `start`, not this constant.
_RRULE_VALIDATION_DTSTART = datetime.datetime(2000, 1, 1)

WEEKDAY_TO_ICAL = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR', 5: 'SA', 6: 'SU'}
_UNSUPPORTED_RRULE_FREQS = frozenset({'HOURLY', 'MINUTELY', 'SECONDLY'})
_UNSUPPORTED_RRULE_PARTS = frozenset({'BYWEEKNO', 'BYYEARDAY', 'WKST'})
_ORDINAL_WEEKDAY = re.compile(r'^([+-]?\d{1,2})(MO|TU|WE|TH|FR|SA|SU)$')
_SFCALENDAR_SINGLE_VALUE_PARTS = ('BYDAY', 'BYMONTHDAY', 'BYMONTH', 'BYSETPOS')
_SFCALENDAR_SET_POSITIONS = frozenset({1, 2, 3, 4, -1, -2})


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

    if abs(n / d * 100) > 999:
        raise ValidationError('The grade does not appear to be valid.')

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

    day_code = WEEKDAY_TO_ICAL[dtstart.weekday()]
    return f'{prefix}{rule_body};BYDAY={day_code}'


def _parse_recurrence_rule(value):
    prefix = value[:6] if value.upper().startswith('RRULE:') else ''
    parts = {}
    for part in value[len(prefix):].split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            parts[k.upper()] = v.upper()
    return prefix, parts


def _join_recurrence_rule(prefix, parts):
    return prefix + ';'.join(f'{k}={v}' for k, v in parts.items())


def _split_ordinal_byday(parts):
    ordinal = _ORDINAL_WEEKDAY.match(parts.get('BYDAY', ''))
    if ordinal and 'BYSETPOS' not in parts:
        parts['BYDAY'] = ordinal.group(2)
        parts['BYSETPOS'] = str(int(ordinal.group(1)))


def normalize_recurrence_rule(value, local_start):
    """
    Rewrite ``value`` into the RRULE subset SfCalendar expands correctly, returning it.

    SfCalendar reads a monthly or yearly weekday only as ``BYDAY=<day>;BYSETPOS=<n>``, so an ordinal
    ``BYDAY=<n><day>`` is split into that form. It expands nothing for a monthly or yearly rule that names no
    day, so the day (and, for yearly, the month) RFC 5545 implies from the series start is made explicit.
    ``local_start`` is that start in the user's time zone, the zone the client expands in. Weekly rules go
    through ``infer_byday_for_weekly_rrule``; anything else, including a rule ``validate_recurrence_rule``
    rejects, is returned unchanged.
    """
    if not value:
        return value

    prefix, parts = _parse_recurrence_rule(value)
    freq = parts.get('FREQ')
    if freq == 'WEEKLY':
        return infer_byday_for_weekly_rrule(_join_recurrence_rule(prefix, parts), local_start)
    if freq not in ('MONTHLY', 'YEARLY'):
        return value

    _split_ordinal_byday(parts)
    if 'BYDAY' not in parts and 'BYMONTHDAY' not in parts:
        if freq == 'YEARLY':
            parts.setdefault('BYMONTH', str(local_start.month))
        parts['BYMONTHDAY'] = str(local_start.day)

    return _join_recurrence_rule(prefix, parts)


def _validate_sfcalendar_monthly_or_yearly(freq, parts):
    """
    Reject a monthly or yearly rule SfCalendar cannot expand, even after ``normalize_recurrence_rule``: it reads
    one value per part, one of a weekday or a month day, and a weekday position of 1-4 or -1/-2, and it throws
    on a weekday without a position or a yearly rule without a month.
    """
    for key in _SFCALENDAR_SINGLE_VALUE_PARTS:
        if ',' in parts.get(key, ''):
            raise ValidationError(f'Multiple {key} values are not supported for FREQ={freq}.')

    if freq == 'MONTHLY' and 'BYMONTH' in parts:
        raise ValidationError('BYMONTH is not supported for FREQ=MONTHLY.')

    by_day = parts.get('BYDAY')
    if by_day and 'BYMONTHDAY' in parts:
        raise ValidationError('BYDAY with BYMONTHDAY is not supported.')

    if by_day:
        ordinal = _ORDINAL_WEEKDAY.match(by_day)
        if ordinal and 'BYSETPOS' in parts:
            raise ValidationError('BYDAY with both an ordinal and BYSETPOS is not supported.')
        if not ordinal and 'BYSETPOS' not in parts:
            raise ValidationError(f'BYDAY without an ordinal or BYSETPOS is not supported for FREQ={freq}.')
        position = int(ordinal.group(1)) if ordinal else int(parts['BYSETPOS'])
        if position not in _SFCALENDAR_SET_POSITIONS:
            raise ValidationError(f'A BYDAY position of {position} is not supported.')
    elif 'BYSETPOS' in parts:
        raise ValidationError('BYSETPOS without BYDAY is not supported.')

    by_month_day = parts.get('BYMONTHDAY')
    if by_month_day and not (1 <= int(by_month_day) <= 31 or int(by_month_day) == -1):
        raise ValidationError(f'A BYMONTHDAY of {by_month_day} is not supported.')

    if freq == 'YEARLY' and (by_day or by_month_day) and 'BYMONTH' not in parts:
        raise ValidationError('BYDAY or BYMONTHDAY without BYMONTH is not supported for FREQ=YEARLY.')


def _validation_dtstart_for(parts):
    if parts.get('UNTIL', '').endswith('Z'):
        return _RRULE_VALIDATION_DTSTART.replace(tzinfo=datetime.timezone.utc)
    return _RRULE_VALIDATION_DTSTART


def validate_recurrence_rule(value):
    """
    Validate that ``value`` is a parseable RFC 5545 RRULE string (e.g. ``FREQ=WEEKLY;BYDAY=MO``).

    Accepts both bare rule bodies and the ``RRULE:`` prefixed form. A reference dtstart is
    supplied to ``rrulestr`` only to satisfy parsing — the real series anchor is the parent
    Event's ``start``.

    Rejects properties that are valid per RFC 5545 but not rendered correctly by SfCalendar:
    FREQ=HOURLY/MINUTELY/SECONDLY (silently produces no instances), BYWEEKNO and BYYEARDAY
    (silently ignored → wrong dates), WKST (silently ignored → wrong week boundaries), and the
    monthly and yearly shapes ``normalize_recurrence_rule`` cannot rewrite into ones it expands.
    """
    if value is None or value == '':
        return

    _, parts = _parse_recurrence_rule(value)

    freq = parts.get('FREQ', '')
    if freq in _UNSUPPORTED_RRULE_FREQS:
        raise ValidationError(f'FREQ={freq} is not supported.')

    for key in _UNSUPPORTED_RRULE_PARTS:
        if key in parts:
            raise ValidationError(f'{key} is not supported.')

    try:
        rrulestr(value, dtstart=_validation_dtstart_for(parts))
    except (ValueError, TypeError) as ex:
        raise ValidationError(f'Invalid RRULE: {ex}')

    if freq in ('MONTHLY', 'YEARLY'):
        _validate_sfcalendar_monthly_or_yearly(freq, parts)


def normalize_recurrence_rule_for_user(value, start, user):
    """
    Normalize ``value`` (see ``normalize_recurrence_rule``) against ``start`` in ``user``'s time zone, the zone the
    client expands it in. Returned unchanged when there is no rule or no start.
    """
    if not value or not start:
        return value
    return normalize_recurrence_rule(value, start.astimezone(ZoneInfo(user.settings.time_zone)))


def prepare_recurrence_rule(value, local_start):
    """
    Normalize ``value`` against ``local_start`` (see ``normalize_recurrence_rule``) and validate the result,
    returning the rule ready to store or serve.

    :raises ValidationError: if SfCalendar cannot expand the rule even once normalized
    """
    normalized = normalize_recurrence_rule(value, local_start)
    validate_recurrence_rule(normalized)
    return normalized


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
