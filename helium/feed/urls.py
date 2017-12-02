"""
Feed URLs.
"""

from django.conf.urls import url

from helium.feed.views.apis.externalcalendarview import ExternalCalendarApiListView, ExternalCalendarApiDetailView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

urlpatterns = [
    url(r'^api/feed/externalcalendars/$', ExternalCalendarApiListView.as_view(), name='api_feed_externalcalendar_list'),
    url(r'^api/feed/externalcalendar/(?P<pk>[0-9]+)/$', ExternalCalendarApiDetailView.as_view(),
        name='api_feed_externalcalendar_detail')
]
