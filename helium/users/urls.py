"""
Users URLs.
"""

from django.conf.urls import url

from helium.users.views.accountviews import account_settings
from helium.users.views.authenticationviews import *

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

urlpatterns = [
    # Authentication URLs
    url(r'^register$', register, name='register'),
    url(r'^login$', login, name='login'),
    url(r'^logout', logout, name='logout'),
    url(r'^forgot', forgot, name='forgot'),

    # Account URLs
    url(r'^account/settings', account_settings, name='settings'),
]
