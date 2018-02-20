import sys

from django.conf import settings as config
from django.conf.urls import include, url
from django.views import static

import helium.auth.urls
import helium.common.urls
import helium.feed.urls
import helium.importexport.urls
import helium.planner.urls

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

urlpatterns = [
    # Include app-specific URL files
    url(r'^', include(helium.common.urls)),
    url(r'^', include(helium.auth.urls)),
    url(r'^', include(helium.feed.urls)),
    url(r'^', include(helium.planner.urls)),
    url(r'^', include(helium.importexport.urls)),
]

if config.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

if config.DEBUG or 'test' in sys.argv:
    # Ensure media files are shown properly when using a dev server
    urlpatterns += [
        url(r'^' + config.MEDIA_URL.lstrip('/') + '(?P<path>.*)$', static.serve, {
            'document_root': config.MEDIA_ROOT})
    ]
