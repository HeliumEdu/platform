from django.conf.urls import url

from helium.feed.views.apis.externalcalendarresourceviews import ExternalCalendarAsEventsResourceView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.apis.privateresourceviews import PrivateEnableResourceView, PrivateDisableResourceView
from helium.feed.views.privateviews import PrivateEventsICALResourceView, PrivateHomeworkICALResourceView, \
    PrivateCourseSchedulesICALResourceView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

urlpatterns = [
    ##############################
    # Unauthenticated URLs
    ##############################
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/events\.ics$', PrivateEventsICALResourceView.as_view(),
        name='feed_private_events_ical'),
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/homework\.ics$', PrivateHomeworkICALResourceView.as_view(),
        name='feed_private_homework_ical'),
    url(r'^feed/private/(?P<slug>[a-zA-Z0-9]+)/courseschedules\.ics$', PrivateCourseSchedulesICALResourceView.as_view(),
        name='feed_private_courseschedules_ical'),

    ##############################
    # Authenticated URLs
    ##############################
    # Resource shortcuts
    url(r'^feed/private/enable/$', PrivateEnableResourceView.as_view({'put': 'enable'}),
        name='feed_private_resource_enable'),
    url(r'^feed/private/disable/$', PrivateDisableResourceView.as_view({'put': 'disable'}),
        name='feed_private_resource_disable'),
    url(r'^feed/externalcalendars/(?P<pk>[0-9]+)/events',
        ExternalCalendarAsEventsResourceView.as_view(),
        name='feed_resource_externalcalendars_events'),

    # ExternalCalendar
    url(r'^feed/externalcalendars/$', ExternalCalendarsApiListView.as_view(),
        name='feed_externalcalendars_list'),
    url(r'^feed/externalcalendars/(?P<pk>[0-9]+)/$', ExternalCalendarsApiDetailView.as_view(),
        name='feed_externalcalendars_detail'),
]
