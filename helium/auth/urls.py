from django.conf.urls import url

from helium.auth.views.apis.userprofileviews import UserProfileApiDetailView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView
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
    url(r'^api/auth/users/(?P<pk>[0-9]+)/$', UserApiDetailView.as_view(), name='api_auth_users_detail'),
    url(r'^api/auth/users/(?P<pk>[0-9]+)/profile', UserProfileApiDetailView.as_view(),
        name='api_auth_users_profile_detail'),
    url(r'^api/auth/users/(?P<pk>[0-9]+)/settings', UserSettingsApiDetailView.as_view(),
        name='api_auth_users_settings_detail'),
]
