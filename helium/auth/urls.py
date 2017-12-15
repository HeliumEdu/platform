"""
Users URLs.
"""

from django.conf.urls import url

from helium.auth.views.apis.userprofileviews import UserProfileApiListView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiListView
from helium.auth.views.apis.userviews import UserApiListView
from helium.auth.views.authenticationviews import *
from helium.auth.views.settingsviews import *

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

urlpatterns = [
    # Authentication URLs
    url(r'^register$', register, name='register'),
    url(r'^verify$', verify, name='verify'),
    url(r'^login$', login, name='login'),
    url(r'^logout', logout, name='logout'),
    url(r'^forgot', forgot, name='forgot'),

    # Account URLs
    url(r'^unsubscribe', unsubscribe, name='unsubscribe'),
    url(r'^settings', settings, name='settings'),

    # API URLs
    url(r'^api/user/$', UserApiListView.as_view(), name='api_user_list'),
    url(r'^api/user/profile', UserProfileApiListView.as_view(), name='api_user_profile_list'),
    url(r'^api/user/settings', UserSettingsApiListView.as_view(), name='api_user_settings_list'),
]
