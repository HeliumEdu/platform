__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime


def local_midnight_as_utc(date, tz):
    """
    Return the UTC datetime that represents midnight on the given date in the given timezone.

    This encodes the storage invariant for all-day calendar items: their `start`/`end` are
    persisted in UTC but represent midnight in the user's local timezone. Crossing that
    invariant (e.g. when a user changes their timezone) requires recomputing the UTC value
    so the local date observed by the user remains stable.

    :param date: A `date` (or `datetime`, of which only the date portion is used).
    :param tz: A `tzinfo` (e.g. `ZoneInfo`) representing the local timezone.
    :return: An aware UTC `datetime` at midnight `tz` on `date`.
    """
    naive = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0)
    aware = naive.replace(tzinfo=tz)
    return aware.astimezone(datetime.timezone.utc)
