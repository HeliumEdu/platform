__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import decimal
import re
import sys

from django.core.exceptions import ValidationError

from helium.common.utils import commonutils


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
