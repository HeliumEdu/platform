"""
Common URLs.
"""

from django.conf import settings as config
from django.conf.urls import include, url
from django.views.generic import RedirectView

from conf.admin import admin_site
from helium.common.views import *

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

urlpatterns = [
    # Admin URLs
    url(r'^admin/', include(admin_site.urls), name='admin'),

    # URL shortcuts
    url(r'^favicon\.ico$', RedirectView.as_view(url=config.STATIC_URL + 'favicon.ico', permanent=True)),

    # Base URL
    url(r'^$', home, name='home'),

    # General URLs
    url(r'^contact', contact, name='contact'),

]

if config.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
