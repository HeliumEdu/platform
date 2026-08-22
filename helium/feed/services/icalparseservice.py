import datetime
import logging

from django.utils import timezone

from helium.common.utils.validators import infer_byday_for_weekly_rrule, validate_recurrence_rule

logger = logging.getLogger(__name__)


def _resolve_component_time_zone(component, default_time_zone):
    """Resolve a VTIMEZONE to a tzinfo from its own offset rules, honoring a non-IANA abbreviation
    TZID (e.g. ``EDT``). Falls back to ``default_time_zone`` if it can't yield a usable tzinfo.
    """
    try:
        return component.to_tz()
    except Exception:
        logger.info('Unresolvable VTIMEZONE TZID %r; falling back to the default time zone.',
                    str(component.get("TZID")))
        return default_time_zone


def _extract_exception_dates(component):
    """Return ISO-8601 UTC strings for any EXDATE entries on the VEVENT, or None.

    EXDATE can appear once with multiple values or as multiple EXDATE lines, so
    ``component.get('EXDATE')`` may return a single vDDDLists or a list of them.
    """
    exdate_field = component.get("EXDATE")
    if not exdate_field:
        return None
    iso_dates = []
    exdate_entries = exdate_field if isinstance(exdate_field, list) else [exdate_field]
    for entry in exdate_entries:
        for vdt in getattr(entry, 'dts', []):
            dt = vdt.dt
            if isinstance(dt, datetime.datetime):
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, datetime.timezone.utc)
                dt = dt.astimezone(datetime.timezone.utc)
            iso_dates.append(dt.isoformat())
    return iso_dates or None


def _extract_extra_dates(component, default_time_zone):
    """Return UTC datetimes for any RDATE entries on the VEVENT.

    RDATE attaches extra one-off occurrences to a series; the caller emits each as a
    standalone event mirroring the parent's duration. Like EXDATE, RDATE may appear once
    with multiple values or as multiple RDATE lines.
    """
    rdate_field = component.get("RDATE")
    if not rdate_field:
        return []
    entries = rdate_field if isinstance(rdate_field, list) else [rdate_field]
    extras = []
    for entry in entries:
        for vdt in getattr(entry, 'dts', []):
            dt = vdt.dt
            if isinstance(dt, datetime.datetime):
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, default_time_zone)
                dt = dt.astimezone(datetime.timezone.utc)
            else:
                dt = timezone.make_aware(
                    datetime.datetime.combine(dt, datetime.time.min), default_time_zone,
                ).astimezone(datetime.timezone.utc)
            extras.append(dt)
    return extras


def _collect_recurrence_id_overrides(calendar, default_time_zone):
    """Map UID to a list of UTC ISO-8601 strings naming the original occurrence datetimes
    that any RECURRENCE-ID overrides replace.

    A moved/edited single occurrence of a recurring series is a separate VEVENT sharing the
    parent's UID and carrying a RECURRENCE-ID. Folding these into the parent's
    ``exception_dates`` avoids rendering both the original slot and the override.
    """
    overrides_by_uid = {}
    time_zone = default_time_zone
    for component in calendar.walk():
        if component.name == "VTIMEZONE":
            time_zone = _resolve_component_time_zone(component, default_time_zone)
            continue
        if component.name != "VEVENT":
            continue
        recurrence_id = component.get("RECURRENCE-ID")
        uid = component.get("UID")
        if recurrence_id is None or uid is None:
            continue
        dt = recurrence_id.dt
        if isinstance(dt, datetime.datetime):
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, time_zone)
            dt = dt.astimezone(datetime.timezone.utc)
        else:
            dt = timezone.make_aware(
                datetime.datetime.combine(dt, datetime.time.min), time_zone,
            ).astimezone(datetime.timezone.utc)
        overrides_by_uid.setdefault(str(uid), []).append(dt.isoformat())
    return overrides_by_uid


def parse_events(calendar, default_time_zone):
    """Yield a normalized dict for each importable VEVENT in the parsed calendar.

    Each dict has: uid, identity, title, all_day, show_end_time, start, end, url, description,
    location, recurrence_rule, exception_dates, extra_starts. All datetimes are UTC.

    :param calendar: A parsed ``icalendar.Calendar``.
    :param default_time_zone: Time zone assumed for naive/floating values (typically the
        user's).
    :return: A generator of normalized VEVENT dicts.
    """
    time_zone = default_time_zone
    recurrence_id_overrides = _collect_recurrence_id_overrides(calendar, time_zone)

    for component in calendar.walk():
        if component.name == "VTIMEZONE":
            time_zone = _resolve_component_time_zone(component, default_time_zone)
            continue
        if component.name != "VEVENT":
            continue

        # Feeds mark deleted events CANCELLED rather than removing them. A CANCELLED
        # RECURRENCE-ID override is captured by the prepass and folded into its parent series,
        # so dropping the override itself here is also correct.
        if str(component.get("STATUS") or "").upper() == "CANCELLED":
            continue

        uid = component.get("UID")

        rrule_component = component.get("RRULE")
        recurrence_rule = rrule_component.to_ical().decode('utf-8') if rrule_component else None
        exception_dates = _extract_exception_dates(component)

        if recurrence_rule:
            override_dates = recurrence_id_overrides.get(str(uid), []) if uid else []
            if override_dates:
                merged = list(exception_dates or [])
                for iso in override_dates:
                    if iso not in merged:
                        merged.append(iso)
                exception_dates = merged

        dt_start = component.get("DTSTART").dt

        if recurrence_rule:
            recurrence_rule = infer_byday_for_weekly_rrule(recurrence_rule, dt_start)
            try:
                validate_recurrence_rule(recurrence_rule)
            except Exception:
                logger.info('Dropping unsupported RRULE from VEVENT: %s', recurrence_rule)
                recurrence_rule = None

        if component.get("DTEND") is not None:
            dt_end = component.get("DTEND").dt
        elif component.get("DURATION") is not None:
            dt_end = dt_start + component.get("DURATION").dt
        else:
            dt_end = datetime.datetime.combine(dt_start, datetime.time.max)

        all_day = not isinstance(dt_start, datetime.datetime)
        show_end_time = isinstance(dt_start, datetime.datetime)

        if all_day:
            dt_start = datetime.datetime.combine(dt_start, datetime.time.min)
        if timezone.is_naive(dt_start):
            dt_start = timezone.make_aware(dt_start, time_zone)
        else:
            dt_start = dt_start.astimezone(time_zone)
        dt_start = dt_start.astimezone(datetime.timezone.utc)

        if all_day:
            dt_end = datetime.datetime.combine(dt_end, datetime.time.min)
        if timezone.is_naive(dt_end):
            dt_end = timezone.make_aware(dt_end, time_zone)
        else:
            dt_end = dt_end.astimezone(time_zone)
        dt_end = dt_end.astimezone(datetime.timezone.utc)

        # An iCal VEVENT without a SUMMARY is malformed, so skip it.
        summary = component.get("SUMMARY")
        if not summary:
            continue

        # RFC 5545 requires UID, but real-world feeds aren't always compliant, so fall back
        # to title-based identity for the (rare) VEVENT missing one.
        identity = str(uid) if uid else summary

        yield {
            'uid': str(uid) if uid else None,
            'identity': identity,
            'title': summary,
            'all_day': all_day,
            'show_end_time': show_end_time,
            'start': dt_start,
            'end': dt_end,
            'url': component.get("URL"),
            'description': component.get("DESCRIPTION"),
            'location': component.get("LOCATION"),
            'recurrence_rule': recurrence_rule,
            'exception_dates': exception_dates,
            'extra_starts': _extract_extra_dates(component, time_zone),
        }
