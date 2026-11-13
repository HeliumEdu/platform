import datetime

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrulestr
from django.utils import timezone

from helium.common import enums
from helium.common.utils.validators import join_recurrence_rule, occurs_within_horizon, parse_recurrence_rule


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


def occurrence_end(first_start, first_end, occurrence_start, tz, all_day=False):
    """
    Return the end of the occurrence starting at ``occurrence_start`` in a series whose first occurrence runs
    ``first_start`` to ``first_end``. A timed occurrence keeps the first one's duration; an all-day occurrence
    keeps its span of local dates, ending on the exclusive next local midnight, as a fixed 24 hours would drift on
    a DST day.

    :param first_start: The aware first occurrence start.
    :param first_end: The aware first occurrence end.
    :param occurrence_start: The aware start of the occurrence to end.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`), the zone the series is expanded in.
    :param all_day: Whether the series is all-day.
    :return: The aware UTC end of the occurrence.
    """
    if not all_day:
        return occurrence_start.astimezone(datetime.timezone.utc) + (first_end - first_start)

    span_days = max((first_end.astimezone(tz).date() - first_start.astimezone(tz).date()).days, 1)
    return local_midnight_as_utc(occurrence_start.astimezone(tz).date() + datetime.timedelta(days=span_days), tz)


def expand_recurrence(rule, start, end, tz, all_day=False, exception_dates=None, not_before=None):
    """
    Lazily expand an RRULE series into its ``(start, end)`` occurrences as aware UTC datetimes, in series order.

    Occurrences keep their wall-clock time in ``tz`` across DST. An all-day series expands on local dates; see
    :func:`occurrence_end` for how each ``end`` is derived. An occurrence is skipped when an exception falls on
    its local date. A date-only ``UNTIL`` includes that whole local day, as SfCalendar reads it. Expansion
    stops at ``enums.RECURRENCE_HORIZON_YEARS`` from now, and a series with no occurrence within
    ``enums.RECURRENCE_HORIZON_YEARS`` of its start yields nothing.

    :param rule: The RRULE string, bare or ``RRULE:`` prefixed.
    :param start: The aware first occurrence start.
    :param end: The aware first occurrence end.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`), the zone the series is expanded in.
    :param all_day: Whether the series is all-day.
    :param exception_dates: ISO-8601 datetimes (iCal EXDATE) whose local date is skipped, or None.
    :param not_before: Aware datetime; occurrences starting before it are not yielded, or None.
    :return: A generator of ``(start, end)`` UTC tuples.
    """
    local_start = start.astimezone(tz)
    skipped_dates = {datetime.datetime.fromisoformat(iso).astimezone(tz).date() for iso in exception_dates or []}

    _, parts = parse_recurrence_rule(rule)
    until = parts.get('UNTIL', '')
    if len(until) == len('YYYYMMDD'):
        parts['UNTIL'] = f'{until}T235959'
    dtstart = local_start if until.endswith('Z') else local_start.replace(tzinfo=None)
    if not occurs_within_horizon(rule, dtstart):
        return
    horizon = timezone.now() + relativedelta(years=enums.RECURRENCE_HORIZON_YEARS)

    for occurrence in rrulestr(join_recurrence_rule('', parts), dtstart=dtstart):
        occurrence = occurrence.replace(tzinfo=tz) if occurrence.tzinfo is None else occurrence.astimezone(tz)
        if occurrence > horizon:
            return
        if occurrence.date() in skipped_dates:
            continue

        if all_day:
            occurrence_start = local_midnight_as_utc(occurrence, tz)
        else:
            occurrence_start = occurrence.astimezone(datetime.timezone.utc)

        if not_before is None or occurrence_start >= not_before:
            yield occurrence_start, occurrence_end(start, end, occurrence_start, tz, all_day)


def shifted_series_bounds(series_start, occurrence_start, new_start, new_end, tz, all_day=False):
    """
    Return where a series starting at ``series_start`` starts and ends once one of its occurrences moves from
    ``occurrence_start`` to ``new_start``..``new_end``: the same number of local days later, at the new wall-clock
    time, with the new duration (all day, the new span of dates).

    :param series_start: The aware series start.
    :param occurrence_start: The aware start of the occurrence that moved.
    :param new_start: The aware new start of that occurrence.
    :param new_end: The aware new end of that occurrence.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`), the zone the series is expanded in.
    :param all_day: Whether the series is all-day.
    :return: The aware UTC ``(start, end)`` of the series.
    """
    new_local = new_start.astimezone(tz)
    day_shift = (new_local.date() - occurrence_start.astimezone(tz).date()).days
    series_date = series_start.astimezone(tz).date() + datetime.timedelta(days=day_shift)

    if all_day:
        start = local_midnight_as_utc(series_date, tz)
    else:
        start = local_time_as_utc(series_date, new_local.time(), tz)
    return start, occurrence_end(new_start, new_end, start, tz, all_day)


def shift_exception_dates(exception_dates, old_start, new_start, tz):
    """
    Move a series' exception dates by the wall-clock distance its start moved in ``tz``, so each still lands on the
    same occurrence of the moved series.

    :param exception_dates: ISO-8601 datetimes (iCal EXDATE), or None.
    :param old_start: The aware series start before the move.
    :param new_start: The aware series start after the move.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`), the zone the series is expanded in.
    :return: The shifted dates as ``Z``-suffixed ISO-8601 strings, or None when given none.
    """
    if not exception_dates:
        return exception_dates

    delta = wall_clock_distance(old_start, new_start, tz)
    shifted = []
    for iso in exception_dates:
        local = datetime.datetime.fromisoformat(iso).astimezone(tz).replace(tzinfo=None) + delta
        shifted.append(as_utc_iso(local.replace(tzinfo=tz)))
    return shifted


def wall_clock_distance(old, new, tz):
    """
    Return how far the wall clock moves in ``tz`` from ``old`` to ``new``, which across a DST change differs from
    the elapsed time by the change.

    :param old: An aware datetime.
    :param new: An aware datetime.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`) the wall clock is read in.
    :return: The `timedelta` between the two wall-clock readings.
    """
    return new.astimezone(tz).replace(tzinfo=None) - old.astimezone(tz).replace(tzinfo=None)


def end_of_day_until(date, tz):
    """
    Format the end of ``date`` in ``tz`` as an iCal ``UNTIL`` value, the last moment a series may occur that day.

    :param date: A `date`.
    :param tz: A `tzinfo` (e.g. `ZoneInfo`), the zone the series is expanded in.
    :return: e.g. "20261218T075959Z".
    """
    end = local_time_as_utc(date, datetime.time(23, 59, 59), tz)
    return end.strftime('%Y%m%dT%H%M%SZ')


def as_utc_iso(instant):
    """
    Format an aware datetime as the ``Z``-suffixed ISO-8601 UTC string the API stores and serves.

    :param instant: An aware datetime.
    :return: e.g. "2026-09-07T16:00:00Z".
    """
    return instant.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


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
