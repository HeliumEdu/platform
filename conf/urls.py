import sys

from django.conf import settings as config
from django.conf.urls import include
from django.urls import re_path
from django.views import static

import helium.auth.urls
import helium.common.urls
import helium.feed.urls
import helium.importexport.urls
import helium.planner.urls

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

urlpatterns = [
    # Include app-specific URL files
    re_path('^', include(helium.common.urls)),
    re_path('^', include(helium.auth.urls)),
    re_path('^', include(helium.feed.urls)),
    re_path('^', include(helium.planner.urls)),
    re_path('^', include(helium.importexport.urls)),
]

if config.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

if config.DEBUG or 'test' in sys.argv:
    # Ensure media files are shown properly when using a dev server
    urlpatterns += [
        re_path(r'^' + config.MEDIA_URL.lstrip('/') + '(?P<path>.*)$', static.serve, {
            'document_root': config.MEDIA_ROOT
        })
    ]
