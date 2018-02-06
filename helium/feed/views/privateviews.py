import logging

from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseNotFound

from helium.feed.services import icalprivateservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


def private_events_ical(request, slug):
    try:
        user = get_user_model().objects.get_by_private_slug(slug)

        ical_feed = icalprivateservice.events_to_private_ical_feed(user)

        response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
        response['Filename'] = 'Helium_' + user.username + '.ics'
        response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '.ics'
        return response
    except get_user_model().DoesNotExist:
        return HttpResponseNotFound()


def private_homework_ical(request, slug):
    try:
        user = get_user_model().objects.get_by_private_slug(slug)

        ical_feed = icalprivateservice.homework_to_private_ical_feed(user)

        response = HttpResponse(ical_feed, content_type='text/calendar; charset=utf-8')
        response['Filename'] = 'Helium_' + user.username + '.ics'
        response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '.ics'
        return response
    except get_user_model().DoesNotExist:
        return HttpResponseNotFound()
