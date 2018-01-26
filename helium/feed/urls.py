from django.conf.urls import url

from helium.feed.views.apis.externalcalendarresourceviews import ExternalCalendarAsExternalEventsView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.feedviews import feed_ical

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

urlpatterns = [
    # Unauthenticated external feed URLs (rely on private slugs for authentication)
    url(r'^feed/([a-zA-Z0-9]+)\.ics$', feed_ical, name='feed_ical'),

    ##############################
    # Authenticated API URLs
    ##############################
    # Resource shortcuts
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/externalevents', ExternalCalendarAsExternalEventsView.as_view(),
        name='api_feed_resource_externalcalendaras_externalevents'),
    # TODO: need to implement enable/disable shortcuts for feeds

    # ExternalCalendar
    url(r'^api/feed/externalcalendars/$', ExternalCalendarsApiListView.as_view(),
        name='api_feed_externalcalendars_list'),
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/$', ExternalCalendarsApiDetailView.as_view(),
        name='api_feed_externalcalendars_detail'),
]
