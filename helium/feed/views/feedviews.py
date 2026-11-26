import logging
from datetime import datetime, timezone as tz
from functools import cached_property

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.http import http_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.exceptions import NotFound

from helium.auth.utils.userutils import is_staff_user
from helium.common.utils import redisutils
from helium.common.views.base import HeliumAPIView
from helium.feed.services import feedservice

logger = logging.getLogger(__name__)


class FeedView(HeliumAPIView):
    """
    A Feed served at a user's private slug. Subclasses provide the Feed's content and last-modified time, and
    its file name, which never names the user.
    """
    filename = None

    def get_last_modified(self, user):
        raise NotImplementedError

    def build_feed(self, user):
        raise NotImplementedError

    @cached_property
    def owner(self):
        """
        The user whose feed this is, or ``None`` when the slug matches no enabled feed.
        """
        slug = self.kwargs.get('private_slug')
        if not slug:
            return None
        UserModel = get_user_model()
        try:
            return UserModel.objects.get_by_private_slug(slug)
        except UserModel.DoesNotExist:
            return None

    def get_throttle_identity(self, request):
        return f'feed-{self.owner.pk}' if self.owner else None

    def serve_feed(self, request):
        user = self.owner
        if user is None:
            raise NotFound()
        self._record_fetch(user)

        last_modified = self.get_last_modified(user)
        etag = feedservice.generate_etag(user.pk, last_modified)

        not_modified = feedservice.check_conditional_request(request, etag, last_modified)
        if not_modified:
            return not_modified

        response = HttpResponse(self.build_feed(user), content_type='text/calendar; charset=utf-8')
        response['Filename'] = self.filename
        response['Content-Disposition'] = f'attachment; filename={self.filename}'
        response['ETag'] = etag
        if last_modified:
            response['Last-Modified'] = http_date(last_modified.timestamp())
        response['Cache-Control'] = f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate'
        return response

    def _record_fetch(self, user):
        try:
            staff_tag = 'true' if is_staff_user(user) else 'false'
            today = datetime.now(tz.utc).date().isoformat()
            key = f'feeds:active_slugs:{staff_tag}:{today}'
            pipe = redisutils.get_redis_client().pipeline()
            pipe.sadd(key, self.kwargs['private_slug'])
            pipe.expire(key, settings.FEED_FETCH_SET_TTL_SECONDS)
            pipe.execute()
        except Exception:
            logger.warning("Failed to record feed fetch", exc_info=True)


@extend_schema(
    tags=['feed.private']
)
class EventsFeedView(FeedView):
    filename = 'Helium_events.ics'

    def get_last_modified(self, user):
        return feedservice.get_events_last_modified(user)

    def build_feed(self, user):
        return feedservice.events_feed(user)

    @extend_schema(
        operation_id='feed_private_events_ical',
        summary='Download the Events Feed',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='The user\'s Events Feed, in iCalendar format.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return the Events Feed (`text/calendar`) for the given private slug: every event instance.
        Intended for subscription in calendar applications (Google Calendar, Apple Calendar, etc.) —
        the response is plain iCalendar text, not JSON.

        Feeds are opt-in. A user's `private_slug` (on their settings) is `null` while Feeds are
        disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the URLs of the Feeds
        (Assignments, Class Schedules and Events, plus the Helium Feed with all three in one calendar).
        `PUT /feed/private/disable/` clears the slug and immediately invalidates all existing Feed URLs.

        A `Content-Disposition: attachment; filename=Helium_events.ics` header is set so that
        browser-initiated requests download the Feed as a file.
        """
        return self.serve_feed(request)


@extend_schema(
    tags=['feed.private']
)
class HomeworkFeedView(FeedView):
    filename = 'Helium_homework.ics'

    def get_last_modified(self, user):
        return feedservice.get_homework_last_modified(user)

    def build_feed(self, user):
        return feedservice.homework_feed(user)

    @extend_schema(
        operation_id='feed_private_homework_ical',
        summary='Download the Assignments Feed',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='The user\'s Assignments Feed, in iCalendar format.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return the Assignments Feed (`text/calendar`) for the given private slug: every homework in a course group
        with `shown_on_calendar` set.
        Intended for subscription in calendar applications (Google Calendar, Apple Calendar, etc.) —
        the response is plain iCalendar text, not JSON.

        Feeds are opt-in. A user's `private_slug` (on their settings) is `null` while Feeds are
        disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the URLs of the Feeds
        (Assignments, Class Schedules and Events, plus the Helium Feed with all three in one calendar).
        `PUT /feed/private/disable/` clears the slug and immediately invalidates all existing Feed URLs.

        A `Content-Disposition: attachment; filename=Helium_homework.ics` header is set so that
        browser-initiated requests download the Feed as a file.
        """
        return self.serve_feed(request)


@extend_schema(
    tags=['feed.private']
)
class CourseSchedulesFeedView(FeedView):
    filename = 'Helium_coursescheduleevents.ics'

    def get_last_modified(self, user):
        return feedservice.get_courseschedules_last_modified(user)

    def build_feed(self, user):
        return feedservice.courseschedules_feed(user)

    @extend_schema(
        operation_id='feed_private_courseschedules_ical',
        summary='Download the Class Schedules Feed',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='The user\'s Class Schedules Feed, in iCalendar format.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return the Class Schedules Feed (`text/calendar`) for the given private slug: every course meeting in a course
        group with `shown_on_calendar` set. Intended for subscription in calendar applications (Google Calendar, Apple
        Calendar, etc.) — the response is plain iCalendar text, not JSON.

        Feeds are opt-in. A user's `private_slug` (on their settings) is `null` while Feeds are
        disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the URLs of the Feeds
        (Assignments, Class Schedules and Events, plus the Helium Feed with all three in one calendar).
        `PUT /feed/private/disable/` clears the slug and immediately invalidates all existing Feed URLs.

        A `Content-Disposition: attachment; filename=Helium_coursescheduleevents.ics` header is
        set so that browser-initiated requests download the Feed as a file.
        """
        return self.serve_feed(request)


@extend_schema(
    tags=['feed.private']
)
class AllFeedView(FeedView):
    filename = 'Helium_all.ics'

    def get_last_modified(self, user):
        return feedservice.get_all_last_modified(user)

    def build_feed(self, user):
        return feedservice.all_feed(user)

    @extend_schema(
        operation_id='feed_private_all_ical',
        summary='Download the Helium Feed',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='The user\'s Helium Feed, in iCalendar format.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return the Helium Feed (`text/calendar`) for the given private slug: the entries of the Assignments,
        Class Schedules and Events Feeds in one calendar.
        Intended for subscription in calendar applications (Google Calendar, Apple Calendar, etc.) —
        the response is plain iCalendar text, not JSON.

        Feeds are opt-in. A user's `private_slug` (on their settings) is `null` while Feeds are
        disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the URLs of the Feeds
        (Assignments, Class Schedules and Events, plus the Helium Feed with all three in one calendar).
        `PUT /feed/private/disable/` clears the slug and immediately invalidates all existing Feed URLs.

        A `Content-Disposition: attachment; filename=Helium_all.ics` header is set so that
        browser-initiated requests download the Feed as a file.
        """
        return self.serve_feed(request)
