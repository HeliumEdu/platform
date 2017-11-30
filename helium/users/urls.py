"""
Users URLs.
"""

from django.conf.urls import url

from helium.users.views.accountviews import *
from helium.users.views.apis.usersettingview import UserSettingView
from helium.users.views.authenticationviews import *

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
    url(r'^api/user/settings', UserSettingView.as_view()),
]
