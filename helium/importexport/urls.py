from django.conf.urls import url

from helium.feed.views.apis.externalcalendarresourceviews import ExternalCalendarAsExternalEventsResourceView
from helium.feed.views.apis.externalcalendarviews import ExternalCalendarsApiListView, ExternalCalendarsApiDetailView
from helium.feed.views.apis.privateresourceviews import PrivateEnableResourceView, PrivateDisableResourceView
from helium.feed.views.privateviews import private_events_ical, private_homework_ical

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

urlpatterns = [
    # Import/Export URLs
    # TODO: implement
]
