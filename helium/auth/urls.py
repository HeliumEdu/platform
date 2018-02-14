from django.conf.urls import url
from rest_framework.authtoken.views import ObtainAuthToken

from helium.auth.views.apis.tokenviews import DestroyAuthToken
from helium.auth.views.apis.userprofileviews import UserProfileApiDetailView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView
from helium.auth.views.authenticationviews import *
from helium.auth.views.generalviews import *

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.5'

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

    ##############################
    # Authentication API URLs
    ##############################
    url(r'^api/auth/token/$', ObtainAuthToken.as_view(), name='api_auth_token'),
    url(r'^api/auth/token/revoke/$', DestroyAuthToken.as_view(), name='api_auth_token_revoke'),

    ##############################
    # Authenticated API URLs
    ##############################
    # User
    url(r'^api/auth/users/(?P<pk>[0-9]+)/$', UserApiDetailView.as_view(), name='api_auth_users_detail'),
    url(r'^api/auth/users/(?P<pk>[0-9]+)/profile', UserProfileApiDetailView.as_view(),
        name='api_auth_users_profile_detail'),
    url(r'^api/auth/users/(?P<pk>[0-9]+)/settings', UserSettingsApiDetailView.as_view(),
        name='api_auth_users_settings_detail'),
]
