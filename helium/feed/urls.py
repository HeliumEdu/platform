from django.conf.urls import url

from helium.feed.views.apis.externalcalendarresourceviews import ExternalCalendarAsExternalEventsResourceView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.apis.privateresourceviews import PrivateEnableResourceView, PrivateDisableResourceView
from helium.feed.views.privateviews import private_events_ical, private_homework_ical

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

urlpatterns = [
    # Unauthenticated external feed URLs (rely on private slugs for authentication)
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/events\.ics$', private_events_ical, name='private_events_ical'),
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/homework\.ics$', private_homework_ical, name='private_homework_ical'),

    ##############################
    # Authenticated API URLs
    ##############################
    # Resource shortcuts
    url(r'^api/feed/private/enable$', PrivateEnableResourceView.as_view(), name='api_feed_private_resource_enable'),
    url(r'^api/feed/private/disable', PrivateDisableResourceView.as_view(), name='api_feed_private_resource_disable'),
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/externalevents', ExternalCalendarAsExternalEventsResourceView.as_view(),
        name='api_feed_resource_externalcalendaras_externalevents'),

    # ExternalCalendar
    url(r'^api/feed/externalcalendars/$', ExternalCalendarsApiListView.as_view(),
        name='api_feed_externalcalendars_list'),
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/$', ExternalCalendarsApiDetailView.as_view(),
        name='api_feed_externalcalendars_detail'),
]
