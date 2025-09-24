__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

import logging

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.exceptions import NotFound

from helium.common.views.views import HeliumAPIView
from helium.feed.services import icalprivateservice

logger = logging.getLogger(__name__)


class PrivateEventsICALResourceView(HeliumAPIView):
    def get(self, request, slug):
        """
        Return a list of all event instances for the authenticated user formatted for an ICAL stream. The response will
        contain a `Content-Disposition` of `attachment; filename=Helium_<username>_events.ics`, so if the request is
        initiated from an HTML form, the response will be a downloadable file in a browser.
        """
        try:
            user = get_user_model().objects.get_by_private_slug(slug)

            ical_feed = icalprivateservice.events_to_private_ical_feed(user)

            response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
            response['Filename'] = 'he_' + user.username + '_events.ics'
            response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '_events.ics'
            return response
        except get_user_model().DoesNotExist:
            raise NotFound()


class PrivateHomeworkICALResourceView(HeliumAPIView):
    def get(self, request, slug):
        """
        Return a list of all homework instances for the authenticated user formatted for an ICAL stream. The response
        will contain a `Content-Disposition` of `attachment; filename=Helium_<username>_homework.ics`, so if the
        request is initiated from an HTML form, the response will be a downloadable file in a browser.
        """
        try:
            user = get_user_model().objects.get_by_private_slug(slug)

            ical_feed = icalprivateservice.homework_to_private_ical_feed(user)

            response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
            response['Filename'] = 'he_' + user.username + '_homework.ics'
            response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '_homework.ics'
            return response
        except get_user_model().DoesNotExist:
            raise NotFound()


class PrivateCourseSchedulesICALResourceView(HeliumAPIView):
    def get(self, request, slug):
        """
        Return a list of all course schedule instances for the authenticated user formatted for an ICAL stream. The
        response will contain a `Content-Disposition` of
        `attachment; filename=Helium_<username>_coursescheduleevents.ics`, so if the request is initiated from an HTML
        form, the response will be a downloadable file in a browser.
        """
        try:
            user = get_user_model().objects.get_by_private_slug(slug)

            ical_feed = icalprivateservice.courseschedules_to_private_ical_feed(user)

            response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
            response['Filename'] = 'he_' + user.username + 'coursescheduleevents.ics'
            response['Content-Disposition'] = 'attachment; ' \
                                              'filename=Helium_' + user.username + '_coursescheduleevents.ics'
            return response
        except get_user_model().DoesNotExist:
            raise NotFound()
