import http.client
import json
import logging
from urllib.error import HTTPError
from urllib.request import Request
from zoneinfo import ZoneInfo

import icalendar
from dateutil import parser
from django.conf import settings
from django.core import validators
from django.core.cache import cache
from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from helium.common import enums, errorcodes
from helium.common.utils import datetimeutils, metricutils
from helium.common.utils.commonutils import HeliumError, deterministic_id
from helium.common.utils.httputils import urlopen_secure
from helium.feed.models import ExternalCalendar
from helium.feed.services.icalparseservice import parse_events
from helium.planner.models import Event
from helium.planner.serializers.eventserializer import GeneratedEventSerializer

logger = logging.getLogger(__name__)

url_validator = validators.URLValidator()


_ERROR_CODES = {
    'bad_response': errorcodes.EXTERNAL_CALENDAR_BAD_RESPONSE,
    'invalid_url': errorcodes.EXTERNAL_CALENDAR_INVALID_URL,
    'unreachable': errorcodes.EXTERNAL_CALENDAR_UNREACHABLE,
    'invalid_calendar': errorcodes.EXTERNAL_CALENDAR_INVALID_CALENDAR,
}


class HeliumICalendarError(HeliumError):
    """Raised when an external calendar's iCalendar URL cannot be fetched or parsed."""

    def __init__(self, message, reason):
        super().__init__(message)

        self.reason = reason
        self.code = _ERROR_CODES[reason]


def _get_cache_prefix(external_calendar):
    return f"users:{external_calendar.user_id}:externalcalendars:{external_calendar.pk}:events"


def record_fetch_failure(external_calendar, error):
    """
    Record a failed fetch against the calendar, disabling it only once it has failed enough
    times in a row to reach the configured threshold, so a transient upstream outage cannot
    take a user's calendar offline.

    :param external_calendar: The ExternalCalendar model instance that failed to sync.
    :param error: The error raised by the failed fetch.
    :return: True if this failure disabled the calendar.
    """
    ExternalCalendar.objects.filter(pk=external_calendar.pk).update(
        consecutive_failures=F('consecutive_failures') + 1,
        last_sync_error=str(error))

    external_calendar.refresh_from_db(fields=['consecutive_failures', 'last_sync_error'])

    metricutils.increment('external_calendar.fetch.failed', extra_tags=[f'reason:{error.reason}'])

    if (external_calendar.consecutive_failures < settings.EXTERNAL_CALENDAR_CONSECUTIVE_FAILURE_THRESHOLD
            or not external_calendar.shown_on_calendar):
        logger.info(f"External Calendar {external_calendar.pk} failure "
                    f"{external_calendar.consecutive_failures}/"
                    f"{settings.EXTERNAL_CALENDAR_CONSECUTIVE_FAILURE_THRESHOLD}: {error}")

        return False

    ExternalCalendar.objects.filter(pk=external_calendar.pk).update(shown_on_calendar=False, updated_at=timezone.now())
    external_calendar.shown_on_calendar = False

    logger.info(f"Disabling External Calendar {external_calendar.pk} after "
                f"{external_calendar.consecutive_failures} consecutive failures")

    metricutils.increment('external_calendar.disabled')

    return True


def record_fetch_success(external_calendar):
    """
    Clear any failure state recorded against the calendar by a previous failed fetch.

    :param external_calendar: The ExternalCalendar model instance that synced successfully.
    """
    if external_calendar.consecutive_failures == 0 and external_calendar.last_sync_error is None:
        return

    ExternalCalendar.objects.filter(pk=external_calendar.pk).update(
        consecutive_failures=0,
        last_sync_error=None)

    external_calendar.consecutive_failures = 0
    external_calendar.last_sync_error = None


def _get_events_from_cache(external_calendar, cached_value, _from=None, to=None):
    events = []
    invalid_data = False

    try:
        for event_data in json.loads(cached_value):
            event = Event(id=event_data['id'],
                          title=event_data['title'],
                          all_day=event_data['all_day'],
                          show_end_time=event_data['show_end_time'],
                          start=parser.parse(event_data['start']),
                          end=parser.parse(event_data['end']),
                          owner_id=event_data['owner_id'],
                          user_id=event_data['user'],
                          calendar_item_type=event_data['calendar_item_type'],
                          url=event_data['url'],
                          color=external_calendar.color,
                          location=event_data.get('location'),
                          comments=event_data['comments'],
                          recurrence_rule=event_data.get('recurrence_rule'),
                          exception_dates=event_data.get('exception_dates'))

            if datetimeutils.event_in_range(event, _from, to):
                events.append(event)
    except (json.JSONDecodeError, KeyError, TypeError):
        invalid_data = True

    if invalid_data:
        events = []
        cache.delete(_get_cache_prefix(external_calendar))

    return events, not invalid_data


def _create_events_from_calendar(external_calendar, calendar, _from=None, to=None):
    events = []
    events_filtered = []

    user = external_calendar.user
    time_zone = ZoneInfo(user.settings.time_zone)

    for parsed in parse_events(calendar, time_zone):
        comments = parsed['description'] or ""

        event = Event(id=deterministic_id(external_calendar.pk, parsed['identity'], parsed['start'].isoformat()),
                      title=parsed['title'],
                      all_day=parsed['all_day'],
                      show_end_time=parsed['show_end_time'],
                      start=parsed['start'],
                      end=parsed['end'],
                      url=parsed['url'],
                      color=external_calendar.color,
                      location=parsed['location'],
                      owner_id=external_calendar.id,
                      comments=comments,
                      user=user,
                      calendar_item_type=enums.EXTERNAL,
                      recurrence_rule=parsed['recurrence_rule'],
                      exception_dates=parsed['exception_dates'])

        events.append(event)

        if datetimeutils.event_in_range(event, _from, to):
            events_filtered.append(event)

        # RDATE: emit one standalone Event per extra occurrence, mirroring the
        # parent's duration. Each becomes a one-off (no RRULE) — SfCalendar
        # only expands a single RRULE per event, so extras must be modeled
        # as independent events.
        duration = parsed['end'] - parsed['start']
        for extra_start in parsed['extra_starts']:
            extra_event = Event(id=deterministic_id(external_calendar.pk, parsed['identity'], extra_start.isoformat()),
                                title=parsed['title'],
                                all_day=parsed['all_day'],
                                show_end_time=parsed['show_end_time'],
                                start=extra_start,
                                end=extra_start + duration,
                                url=parsed['url'],
                                color=external_calendar.color,
                                location=parsed['location'],
                                owner_id=external_calendar.id,
                                comments=comments,
                                user=user,
                                calendar_item_type=enums.EXTERNAL)
            events.append(extra_event)
            if datetimeutils.event_in_range(extra_event, _from, to):
                events_filtered.append(extra_event)

    serializer = GeneratedEventSerializer(events, many=True)
    events_json = json.dumps(serializer.data)
    if len(events_json.encode('utf-8')) <= settings.GENERATED_EVENTS_MAX_CACHEABLE_SIZE:
        cache.set(_get_cache_prefix(external_calendar), events_json, settings.GENERATED_EVENTS_CACHE_TTL_SECONDS)

        ExternalCalendar.objects.filter(pk=external_calendar.pk).update(last_index=timezone.now())
    else:
        logger.warning("Cache size {max_cache_size} exceeded max, External Calendar {id}".format(
            max_cache_size=len(events_json.encode('utf-8')),
            id=external_calendar.pk))

        metricutils.increment('task.cache.max-size-exceeded')

    record_fetch_success(external_calendar)

    return events_filtered


def invalidate_calendar_cache(external_calendar):
    cache.delete(_get_cache_prefix(external_calendar))

    ExternalCalendar.objects.filter(pk=external_calendar.pk).update(
        etag=None,
        last_modified_header=None,
        last_index=None,
        last_sync_error=None,
        consecutive_failures=0,
    )

    logger.info(f"Cache invalidated for External Calendar {external_calendar.pk}")


def validate_url(url):
    """
    Validates that a given URL returns valid iCalendar data. Validation includes both simple HTTP validation as well as
    downloading and parsing the calendar itself to ensure it is valid. As such, since we parse the full calendar to
    ensure its validity, a Calendar object is also returned if validation is successful.

    :param url: The iCalendar URL to validate
    :return: The validated calendar, as a Calendar object
    """
    try:
        url_validator(url)

        response = urlopen_secure(url)

        if response.getcode() != status.HTTP_200_OK:
            raise HeliumICalendarError("The URL did not return a valid response.", 'bad_response')

        return icalendar.Calendar.from_ical(response.read())
    except ValidationError as ex:
        logger.info(f"The URL is invalid: {ex}")

        raise HeliumICalendarError(ex.message, 'invalid_url')
    except (OSError, http.client.HTTPException) as ex:
        logger.info(f"The URL is not reachable: {ex}")

        raise HeliumICalendarError("The URL is not reachable.", 'unreachable')
    except ValueError as ex:
        logger.info(f"The URL did not return a valid calendar: {ex}")

        raise HeliumICalendarError("The URL did not return a valid calendar.", 'invalid_calendar')


def fetch_icalendar_conditional(external_calendar):
    """
    Fetches an external calendar's iCalendar URL using conditional HTTP requests (ETag/If-Modified-Since).

    If the calendar has not been modified since the last fetch (304 Not Modified),
    returns None to indicate the existing cache should be used.

    If the calendar has been modified or this is the first fetch, returns the parsed
    Calendar object and updates the external_calendar's etag and last_modified_header.

    :param external_calendar: The ExternalCalendar model instance
    :return: Parsed icalendar.Calendar object, or None if not modified (304)
    :raises HeliumICalendarError: If the URL is unreachable or returns invalid data
    """
    try:
        request = Request(external_calendar.url)

        # Add conditional request headers if we have cached values
        if external_calendar.etag:
            request.add_header('If-None-Match', external_calendar.etag)
        if external_calendar.last_modified_header:
            request.add_header('If-Modified-Since', external_calendar.last_modified_header)

        try:
            response = urlopen_secure(request)
        except HTTPError as ex:
            if ex.code != status.HTTP_304_NOT_MODIFIED:
                raise
            logger.info(f"External Calendar {external_calendar.pk} not modified (304)")
            return None
        response_code = response.getcode()

        if response_code != status.HTTP_200_OK:
            raise HeliumICalendarError("The URL did not return a valid response.", 'bad_response')

        # Store caching headers from the response for next time
        new_etag = response.getheader('ETag')
        new_last_modified = response.getheader('Last-Modified')

        if new_etag or new_last_modified:
            update_fields = []
            if new_etag and new_etag != external_calendar.etag:
                external_calendar.etag = new_etag
                update_fields.append('etag')
            if new_last_modified and new_last_modified != external_calendar.last_modified_header:
                external_calendar.last_modified_header = new_last_modified
                update_fields.append('last_modified_header')
            if update_fields:
                external_calendar.save(update_fields=update_fields)

        metricutils.increment('external_calendar.fetched')
        return icalendar.Calendar.from_ical(response.read())

    except (OSError, http.client.HTTPException) as ex:
        logger.info(f"The URL is not reachable: {ex}")
        raise HeliumICalendarError("The URL is not reachable.", 'unreachable')
    except ValueError as ex:
        logger.info(f"The URL did not return a valid calendar: {ex}")
        raise HeliumICalendarError("The URL did not return a valid calendar.", 'invalid_calendar')


def calendar_to_events(external_calendar, _from=None, to=None):
    """
    For the given external calendar model and parsed iCalendar data, convert each item in the calendar to an event
    resources.

    :param external_calendar: The external calendar source that is referenced by the calendar object.
    :param _from: The earliest date by which to filter results.
    :param to: The last date by which to filter results.
    :return: A list of event resources.
    """
    events = []

    cached = False
    cached_value = cache.get(_get_cache_prefix(external_calendar))
    if cached_value:
        events, cached = _get_events_from_cache(external_calendar, cached_value, _from, to)

    if not cached:
        calendar = validate_url(external_calendar.url)

        events = _create_events_from_calendar(external_calendar, calendar, _from, to)

    return events


def reindex_stale_caches(calendar_ids=None):
    """
    :param calendar_ids: Optional list of ExternalCalendar PKs to reindex. When provided, bypasses
        the stale-cache check and targets only those specific calendars. When None (default),
        reindexes all calendars whose cache is stale.
    """
    reindexed = []
    not_modified = []

    if calendar_ids is not None:
        queryset = (ExternalCalendar.objects
                    .filter(pk__in=calendar_ids)
                    .select_related('user', 'user__settings'))
    else:
        queryset = ExternalCalendar.objects.needs_recached().select_related('user', 'user__settings')

    for external_calendar in queryset.iterator():
        logger.info(f"Reindexing External Calendar {external_calendar.pk}")

        try:
            calendar = fetch_icalendar_conditional(external_calendar)

            if calendar is None:
                # A 304 leaves the cache standing, so only its freshness window needs extending
                external_calendar.last_index = timezone.now()
                external_calendar.save(update_fields=['last_index'])
                record_fetch_success(external_calendar)
                not_modified.append(external_calendar)
            else:
                cache.delete(_get_cache_prefix(external_calendar))
                _create_events_from_calendar(external_calendar, calendar)
                reindexed.append(external_calendar)

        except HeliumICalendarError as e:
            record_fetch_failure(external_calendar, e)
        except SoftTimeLimitExceeded:
            # The task is out of budget; swallowing this would let the sweep run unbounded,
            # since no hard time limit backs it up.
            raise
        except Exception:
            logger.error(f"Unexpected error reindexing External Calendar {external_calendar.pk}, "
                         f"skipping it so the sweep can continue", exc_info=True)

            metricutils.increment('external_calendar.fetch.failed', extra_tags=['reason:unexpected'])

    logger.info(f"Done reindexing: {len(reindexed)} updated, {len(not_modified)} not modified")
