from django.urls import path

from helium.feed.views.apis.externalcalendaraseventsviews import ExternalCalendarAsEventsListView, \
    UserExternalCalendarAsEventsListView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.apis.feedresourceviews import FeedsEnableView, FeedsDisableView
from helium.feed.views.feedviews import EventsFeedView, HomeworkFeedView, \
    CourseSchedulesFeedView, AllFeedView

urlpatterns = [
    ##############################
    # Unauthenticated URLs
    ##############################
    path('feed/private/<str:private_slug>/events.ics', EventsFeedView.as_view(),
         name='feed_events'),
    path('feed/private/<str:private_slug>/homework.ics', HomeworkFeedView.as_view(),
         name='feed_homework'),
    path('feed/private/<str:private_slug>/courseschedules.ics', CourseSchedulesFeedView.as_view(),
         name='feed_courseschedules'),
    path('feed/private/<str:private_slug>/all.ics', AllFeedView.as_view(),
         name='feed_all'),

    ##############################
    # Authenticated URLs
    ##############################
    # Resource shortcuts
    path('feed/private/enable/', FeedsEnableView.as_view({'put': 'enable'}),
         name='feed_enable'),
    path('feed/private/disable/', FeedsDisableView.as_view({'put': 'disable'}),
         name='feed_disable'),
    path('feed/externalcalendars/<int:pk>/events/',
         ExternalCalendarAsEventsListView.as_view(),
         name='feed_resource_externalcalendars_events'),
    path('feed/externalcalendars/events/',
         UserExternalCalendarAsEventsListView.as_view(),
         name='feed_externalcalendars_events'),

    # ExternalCalendar
    path('feed/externalcalendars/', ExternalCalendarsApiListView.as_view(),
         name='feed_externalcalendars_list'),
    path('feed/externalcalendars/<int:pk>/', ExternalCalendarsApiDetailView.as_view(),
         name='feed_externalcalendars_detail'),
]
