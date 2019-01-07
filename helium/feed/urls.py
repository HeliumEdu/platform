from django.urls import path

from helium.feed.views.apis.externalcalendarresourceviews import ExternalCalendarAsEventsResourceView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.apis.privateresourceviews import PrivateEnableResourceView, PrivateDisableResourceView
from helium.feed.views.privateviews import PrivateEventsICALResourceView, PrivateHomeworkICALResourceView, \
    PrivateCourseSchedulesICALResourceView

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

urlpatterns = [
    ##############################
    # Unauthenticated URLs
    ##############################
    path('feed/private/<slug>/events.ics', PrivateEventsICALResourceView.as_view(),
         name='feed_private_events_ical'),
    path('feed/private/<slug>/homework.ics', PrivateHomeworkICALResourceView.as_view(),
         name='feed_private_homework_ical'),
    path('feed/private/<slug>/courseschedules.ics', PrivateCourseSchedulesICALResourceView.as_view(),
         name='feed_private_courseschedules_ical'),

    ##############################
    # Authenticated URLs
    ##############################
    # Resource shortcuts
    path('feed/private/enable/', PrivateEnableResourceView.as_view({'put': 'enable'}),
         name='feed_private_resource_enable'),
    path('feed/private/disable/', PrivateDisableResourceView.as_view({'put': 'disable'}),
         name='feed_private_resource_disable'),
    path('feed/externalcalendars/<int:pk>/events/',
         ExternalCalendarAsEventsResourceView.as_view(),
         name='feed_resource_externalcalendars_events'),

    # ExternalCalendar
    path('feed/externalcalendars/', ExternalCalendarsApiListView.as_view(),
         name='feed_externalcalendars_list'),
    path('feed/externalcalendars/<int:pk>/', ExternalCalendarsApiDetailView.as_view(),
         name='feed_externalcalendars_detail'),
]
