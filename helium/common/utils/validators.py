__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import decimal
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

        if n > sys.maxsize or d > sys.maxsize:
            raise ValidationError(f'Values must be less than or equal to {sys.maxsize}.')

        return f'{commonutils.remove_exponent(n.normalize())}/{commonutils.remove_exponent(d.normalize())}'
    except:
        raise ValidationError('The fraction must contain valid integers.')
