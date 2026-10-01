from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from helium.common.utils.validators import validate_and_normalize_date_csv


def validate_start_before_end(attrs, instance):
    """
    Raise if the effective `start` is after the effective `end`, where a value missing from `attrs` falls back to
    the instance being updated.

    :param attrs: The serializer's incoming attributes.
    :param instance: The instance being updated, or None on create.
    :return: The effective `start`.
    """
    start = attrs.get('start', None)
    if not start and instance:
        start = instance.start
    end = attrs.get('end', None)
    if not end and instance:
        end = instance.end

    if start and end and start > end:
        raise serializers.ValidationError("The 'start' must be before the 'end'")

    return start


def validate_date_range_and_exceptions(attrs, instance, range_label):
    """
    Raise if the effective `start_date` is after the effective `end_date`, then validate and normalize `exceptions`
    against that range whenever the exceptions or either bound is being set. Values missing from `attrs` fall back
    to the instance being updated.

    :param attrs: The serializer's incoming attributes; `exceptions` is replaced with its normalized form.
    :param instance: The instance being updated, or None on create.
    :param range_label: How the range is described in exception errors (e.g. "class date range").
    """
    start_date = attrs.get('start_date', None)
    if not start_date and instance:
        start_date = instance.start_date
    end_date = attrs.get('end_date', None)
    if not end_date and instance:
        end_date = instance.end_date

    if start_date and end_date and start_date > end_date:
        raise serializers.ValidationError("The 'start_date' must be before the 'end_date'")

    if 'exceptions' in attrs or 'start_date' in attrs or 'end_date' in attrs:
        exceptions = attrs.get('exceptions', None)
        if exceptions is None and instance:
            exceptions = instance.exceptions
        if exceptions:
            try:
                attrs['exceptions'] = validate_and_normalize_date_csv(
                    exceptions, start_date, end_date, range_label=range_label)
            except DjangoValidationError as e:
                raise serializers.ValidationError({'exceptions': e.message})
