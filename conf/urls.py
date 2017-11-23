"""
Base URLs.
"""

from django.conf import settings as config
from django.conf.urls import include, url
from django.contrib.sitemaps.views import sitemap

import helium.common.urls
import helium.users.urls
import helium.planner.urls
from conf.sitemaps import StaticViewSitemap

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

handler500 = 'helium.common.views.internal_server_error'
handler400 = 'helium.common.views.bad_request'
handler401 = 'helium.common.views.unauthorized'
handler403 = 'helium.common.views.forbidden'

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    # Include app-specific URL files
    url(r'^', include(helium.common.urls)),
    url(r'^', include(helium.users.urls)),
    url(r'^', include(helium.planner.urls)),

    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}),
]

if config.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
