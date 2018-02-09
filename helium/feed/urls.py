from django.conf.urls import url

from helium.feed.views.apis.externalcalendarresourceviews import ExternalCalendarAsEventsResourceView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.apis.privateresourceviews import PrivateEnableResourceView, PrivateDisableResourceView
from helium.feed.views.privateviews import PrivateEventsICALView, PrivateHomeworkICALView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

urlpatterns = [
    # Unauthenticated external feed URLs (rely on private slugs for authentication)
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/events\.ics$', PrivateEventsICALView.as_view(),
        name='feed_private_events_ical'),
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/homework\.ics$', PrivateHomeworkICALView.as_view(),
        name='feed_private_homework_ical'),

    ##############################
    # Authenticated API URLs
    ##############################
    # Resource shortcuts
    url(r'^api/feed/private/enable/$', PrivateEnableResourceView.as_view(), name='api_feed_private_resource_enable'),
    url(r'^api/feed/private/disable/$', PrivateDisableResourceView.as_view(), name='api_feed_private_resource_disable'),
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/externalevents',
        ExternalCalendarAsEventsResourceView.as_view(),
        name='api_feed_resource_externalcalendaras_externalevents'),

    # ExternalCalendar
    url(r'^api/feed/externalcalendars/$', ExternalCalendarsApiListView.as_view(),
        name='api_feed_externalcalendars_list'),
    url(r'^api/feed/externalcalendars/(?P<pk>[0-9]+)/$', ExternalCalendarsApiDetailView.as_view(),
        name='api_feed_externalcalendars_detail'),
]
