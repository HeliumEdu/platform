from decimal import Decimal

from django.core.exceptions import ValidationError

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class HeliumError(Exception):
    pass


def remove_exponent(d):
    """
    Remove the exponent, which may be present in a Decimal.

    :param d: the Decimal number which may contain an exponent
    :return: a number without an exponent
    """
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()


def fraction_validator(value):
    """
    Ensure the given value is a valid fraction (1235/1235) with valid numbers on either side of the ratio. If not,
    raise a validation error.
    """
    split = value.split('/')
    if len(split) != 2:
        raise ValidationError('Enter a valid fraction of the format \'x/y\'.')

    try:
        n = Decimal(split[0].strip())
    except:
        raise ValidationError('The numerator is not a valid integer.')

    try:
        d = Decimal(split[1].strip())
    except:
        raise ValidationError('The denominator is not a valid integer.')

    if n > 2147483647 or d > 2147483647:
        raise ValidationError('Values must be less than or equal to 2147483647.')

    try:
        return '{}/{}'.format(remove_exponent(n.normalize()), remove_exponent(d.normalize()))
    except:
        raise ValidationError('An error occurred when validating the fraction.')
