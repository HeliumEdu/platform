__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.http import http_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.exceptions import NotFound

from helium.common.views.base import HeliumAPIView
from helium.feed.services import icalprivateservice

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.private']
)
class PrivateEventsICALResourceView(HeliumAPIView):
    @extend_schema(
        operation_id='feed_private_events_ical',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='iCalendar (.ics) feed of the user\'s events.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return an iCalendar (`text/calendar`) feed of all event instances for the given private slug.
        Intended for subscription in calendar applications (Google Calendar, Apple Calendar, etc.) —
        the response is plain iCalendar text, not JSON.

        Private feeds are opt-in. A user's `private_slug` (on their settings) is `null` while feeds
        are disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the three
        feed URLs (events, homework, course schedules). `PUT /feed/private/disable/` clears the slug
        and immediately invalidates all existing feed URLs.

        A `Content-Disposition: attachment; filename=Helium_<user>_events.ics` header is set so that
        browser-initiated requests download the feed as a file.
        """
        UserModel = get_user_model()

        try:
            user = UserModel.objects.get_by_private_slug(private_slug)

            last_modified = icalprivateservice.get_events_last_modified(user)
            etag = icalprivateservice.generate_etag(user.pk, last_modified)

            not_modified = icalprivateservice.check_conditional_request(request, etag, last_modified)
            if not_modified:
                return not_modified

            ical_feed = icalprivateservice.events_to_private_ical_feed(user)

            response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
            response['Filename'] = 'he_' + user.username + '_events.ics'
            response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '_events.ics'
            response['ETag'] = etag
            if last_modified:
                response['Last-Modified'] = http_date(last_modified.timestamp())
            response['Cache-Control'] = f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate'
            return response
        except UserModel.DoesNotExist:
            raise NotFound()


@extend_schema(
    tags=['feed.private']
)
class PrivateHomeworkICALResourceView(HeliumAPIView):
    @extend_schema(
        operation_id='feed_private_homework_ical',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='iCalendar (.ics) feed of the user\'s homework.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return an iCalendar (`text/calendar`) feed of all homework instances for the given private slug.
        Intended for subscription in calendar applications (Google Calendar, Apple Calendar, etc.) —
        the response is plain iCalendar text, not JSON.

        Private feeds are opt-in. A user's `private_slug` (on their settings) is `null` while feeds
        are disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the three
        feed URLs (events, homework, course schedules). `PUT /feed/private/disable/` clears the slug
        and immediately invalidates all existing feed URLs.

        A `Content-Disposition: attachment; filename=Helium_<user>_homework.ics` header is set so that
        browser-initiated requests download the feed as a file.
        """
        UserModel = get_user_model()

        try:
            user = UserModel.objects.get_by_private_slug(private_slug)

            last_modified = icalprivateservice.get_homework_last_modified(user)
            etag = icalprivateservice.generate_etag(user.pk, last_modified)

            not_modified = icalprivateservice.check_conditional_request(request, etag, last_modified)
            if not_modified:
                return not_modified

            ical_feed = icalprivateservice.homework_to_private_ical_feed(user)

            response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
            response['Filename'] = 'he_' + user.username + '_homework.ics'
            response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '_homework.ics'
            response['ETag'] = etag
            if last_modified:
                response['Last-Modified'] = http_date(last_modified.timestamp())
            response['Cache-Control'] = f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate'
            return response
        except UserModel.DoesNotExist:
            raise NotFound()


@extend_schema(
    tags=['feed.private']
)
class PrivateCourseSchedulesICALResourceView(HeliumAPIView):
    @extend_schema(
        operation_id='feed_private_courseschedules_ical',
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='iCalendar (.ics) feed of the user\'s course schedules.'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return an iCalendar (`text/calendar`) feed of all course schedule instances for the given
        private slug. Intended for subscription in calendar applications (Google Calendar, Apple
        Calendar, etc.) — the response is plain iCalendar text, not JSON.

        Private feeds are opt-in. A user's `private_slug` (on their settings) is `null` while feeds
        are disabled; calling `PUT /feed/private/enable/` generates a new slug and returns the three
        feed URLs (events, homework, course schedules). `PUT /feed/private/disable/` clears the slug
        and immediately invalidates all existing feed URLs.

        A `Content-Disposition: attachment; filename=Helium_<user>_coursescheduleevents.ics` header is
        set so that browser-initiated requests download the feed as a file.
        """
        UserModel = get_user_model()

        try:
            user = UserModel.objects.get_by_private_slug(private_slug)

            last_modified = icalprivateservice.get_courseschedules_last_modified(user)
            etag = icalprivateservice.generate_etag(user.pk, last_modified)

            not_modified = icalprivateservice.check_conditional_request(request, etag, last_modified)
            if not_modified:
                return not_modified

            ical_feed = icalprivateservice.courseschedules_to_private_ical_feed(user)

            response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
            response['Filename'] = 'he_' + user.username + 'coursescheduleevents.ics'
            response['Content-Disposition'] = 'attachment; ' \
                                              'filename=Helium_' + user.username + '_coursescheduleevents.ics'
            response['ETag'] = etag
            if last_modified:
                response['Last-Modified'] = http_date(last_modified.timestamp())
            response['Cache-Control'] = f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate'
            return response
        except UserModel.DoesNotExist:
            raise NotFound()
