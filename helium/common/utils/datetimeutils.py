import datetime

from django.utils import timezone

from helium.common import enums


def local_midnight_as_utc(date, tz):
    """
    Return the UTC datetime that represents midnight on the given date in the given timezone.

    :param date: A `date` (or `datetime`, of which only the date portion is used).
    :param tz: A `tzinfo` (e.g. `ZoneInfo`) representing the local timezone.
    :return: An aware UTC `datetime` at midnight `tz` on `date`.
    """
    naive = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0)
    aware = naive.replace(tzinfo=tz)
    return aware.astimezone(datetime.timezone.utc)


def local_time_as_utc(date, time, tz):
    """
    Return the UTC datetime for a wall-clock time on the given date in the given timezone.

    :param date: A `date` (or `datetime`, of which only the date portion is used).
    :param time: A naive `time` read as wall-clock time in `tz`.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`) representing the local timezone.
    :return: An aware UTC `datetime`.
    """
    return datetime.datetime.combine(date, time).replace(tzinfo=tz).astimezone(datetime.timezone.utc)


def offset_to_timedelta(offset, offset_type):
    """
    Convert a reminder offset into the `timedelta` it spans.

    :param offset: The offset amount.
    :param offset_type: A `REMINDER_OFFSET_TYPE_CHOICES` value (minutes, hours, days or weeks).
    :return: The offset as a `timedelta`.
    """
    return datetime.timedelta(**{enums.REMINDER_OFFSET_TYPE_CHOICES[offset_type][1]: int(offset)})


def event_in_range(event, _from, to):
    """
    Return whether an event falls in the inclusive `_from`..`to` range: its start or end is inside the range, it
    spans the whole range, or it is a recurring series that starts by the end of the range. Always True when either
    bound is missing.

    :param event: An object with aware `start` and `end` datetimes and a `recurrence_rule`.
    :param _from: The range start, or None.
    :param to: The range end, or None.
    :return: True if the event belongs in the range.
    """
    if _from and to and not (
            (_from <= event.start <= to or _from <= event.end <= to) or
            (event.start <= _from and event.end >= to) or
            (event.recurrence_rule and event.start <= to)):
        return False

    return True


def earliest_local_date():
    """
    Return the current date in the westernmost timezone (UTC-12), the earliest local date anywhere.

    :return: A `date` on or before every user's local date.
    """
    return (timezone.now() - datetime.timedelta(hours=12)).date()


def _twelve_hour(dt):
    return dt.hour % 12 or 12


def format_date(dt, user_settings):
    """
    Format a datetime as a weekday and word-month date in the user's day/month order.

    :param dt: An aware `datetime` already resolved to the user's timezone.
    :param user_settings: The `UserSettings` whose `date_format` decides the order.
    :return: e.g. "Fri, Sep 4" (MDY) or "Fri, 4 Sep" (DMY).
    """
    if user_settings.date_format == enums.MDY:
        return f'{dt:%a}, {dt:%b} {dt.day}'
    return f'{dt:%a}, {dt.day} {dt:%b}'


def format_time(dt, user_settings, omit_zero_minutes=False):
    """
    Format a datetime's time on the user's 12-hour or 24-hour clock.

    :param dt: An aware `datetime` already resolved to the user's timezone.
    :param user_settings: The `UserSettings` whose `time_format` decides the clock.
    :param omit_zero_minutes: Drop ":00" on the 12-hour clock, e.g. "3 PM"; 24-hour always keeps minutes.
    :return: e.g. "3:05 PM", "3 PM" or "15:05".
    """
    if user_settings.time_format == enums.TWENTY_FOUR_HOUR:
        return f'{dt:%H:%M}'
    if omit_zero_minutes and dt.minute == 0:
        return f'{_twelve_hour(dt)} {dt:%p}'
    return f'{_twelve_hour(dt)}:{dt:%M} {dt:%p}'


def format_date_time(dt, user_settings):
    """
    Format a datetime as :func:`format_date` and :func:`format_time` joined with "at".

    :param dt: An aware `datetime` already resolved to the user's timezone.
    :param user_settings: The `UserSettings` deciding date order and clock.
    :return: e.g. "Fri, Sep 4 at 3:05 PM" or "Fri, 4 Sep at 15:05".
    """
    return f'{format_date(dt, user_settings)} at {format_time(dt, user_settings)}'


def format_short_time(dt, user_settings):
    """
    Format a datetime as a weekday and short time, omitting zero minutes on the 12-hour clock.

    :param dt: An aware `datetime` already resolved to the user's timezone.
    :param user_settings: The `UserSettings` whose `time_format` decides the clock.
    :return: e.g. "Tue, 11 AM", "Tue, 11:30 AM" or "Tue, 13:00".
    """
    return f'{dt:%a}, {format_time(dt, user_settings, omit_zero_minutes=True)}'
