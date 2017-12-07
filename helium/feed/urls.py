"""
Feed URLs.
"""

from django.conf.urls import url

from helium.feed.views.apis.externalcalendarview import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.feeds import feed_ical

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

urlpatterns = [
    # Unauthenticated external feed URLs (rely on private slugs for authentication)
    url(r'^feed/([a-zA-Z0-9]+)\.ics$', feed_ical, name='feed_ical'),

    # Authenticated feed API URLs
    url(r'^api/feed/externalcalendars/$', ExternalCalendarsApiListView.as_view(), name='api_feed_externalcalendars_list'),
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/$', ExternalCalendarsApiDetailView.as_view(),
        name='api_feed_externalcalendars_detail'),
]
