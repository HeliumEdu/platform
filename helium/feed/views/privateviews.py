__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

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
    tags=['feed.private.event']
)
class PrivateEventsICALResourceView(HeliumAPIView):
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='iCalendar file containing events'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return a list of all event instances for the private slug (defined in a user's settings) formatted for an ICAL stream. The response will
        contain a `Content-Disposition` of `attachment; filename=Helium_<username>_events.ics`, so if the request is
        initiated from an HTML form, the response will be a downloadable file in a browser.
        """
        try:
            user = get_user_model().objects.get_by_private_slug(private_slug)

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
            response['Cache-Control'] = 'private, max-age=0, must-revalidate'
            return response
        except get_user_model().DoesNotExist:
            raise NotFound()


@extend_schema(
    tags=['feed.private.event']
)
class PrivateHomeworkICALResourceView(HeliumAPIView):
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='iCalendar file containing homework'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return a list of all homework instances for the private slug (defined in a user's settings) for an ICAL stream.
        The response will contain a `Content-Disposition` of `attachment; filename=Helium_<username>_homework.ics`,
        so if the request is initiated from an HTML form, the response will be a downloadable file in a browser.
        """
        try:
            user = get_user_model().objects.get_by_private_slug(private_slug)

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
            response['Cache-Control'] = 'private, max-age=0, must-revalidate'
            return response
        except get_user_model().DoesNotExist:
            raise NotFound()


@extend_schema(
    tags=['feed.private.event']
)
class PrivateCourseSchedulesICALResourceView(HeliumAPIView):
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='iCalendar file containing course schedules'
            )
        }
    )
    def get(self, request, private_slug):
        """
        Return a list of all course schedule instances for the private slug (defined in a user's settings) for an ICAL
        stream. The response will contain a `Content-Disposition` of
        `attachment; filename=Helium_<username>_coursescheduleevents.ics`, so if the request is initiated from an HTML
        form, the response will be a downloadable file in a browser.
        """
        try:
            user = get_user_model().objects.get_by_private_slug(private_slug)

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
            response['Cache-Control'] = 'private, max-age=0, must-revalidate'
            return response
        except get_user_model().DoesNotExist:
            raise NotFound()
