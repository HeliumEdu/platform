from django.conf.urls import url

from helium.auth.views.apis.tokenviews import ObtainHeliumAuthToken, DestroyHeliumAuthToken
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
    url(r'^api/auth/token/$', ObtainHeliumAuthToken.as_view(), name='api_auth_token'),
    url(r'^api/auth/token/revoke/$', DestroyHeliumAuthToken.as_view(), name='api_auth_token_revoke'),

    ##############################
    # Authenticated API URLs
    ##############################
    # User
    url(r'^api/auth/user/$', UserApiDetailView.as_view(), name='api_auth_user_detail'),
    url(r'^api/auth/user/profile/$', UserProfileApiDetailView.as_view(),
        name='api_auth_user_profile_detail'),
    url(r'^api/auth/user/settings/$', UserSettingsApiDetailView.as_view(),
        name='api_auth_user_settings_detail'),
]
