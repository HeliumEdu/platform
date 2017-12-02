"""
Users URLs.
"""

from django.conf.urls import url

from helium.auth.views.accountviews import *
from helium.auth.views.apis.userprofileview import UserProfileApiView
from helium.auth.views.apis.usersettingsview import UserSettingsApiView
from helium.auth.views.apis.userview import UserApiView
from helium.auth.views.authenticationviews import *

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
    url(r'^settings', settings, name='settings'),

    # API URLs
    url(r'^api/user/$', UserApiView.as_view(), name='api_user'),
    url(r'^api/user/profile', UserProfileApiView.as_view(), name='api_user_profile'),
    url(r'^api/user/settings', UserSettingsApiView.as_view(), name='api_user_settings'),
]
