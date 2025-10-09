__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.12.0"

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

urlpatterns = [
    # Include app-specific URL files
    re_path('^', include(helium.common.urls)),
    re_path('^', include(helium.auth.urls)),
    re_path('^', include(helium.feed.urls)),
    re_path('^', include(helium.planner.urls)),
    re_path('^', include(helium.importexport.urls)),
]

if config.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [
            re_path(r'^__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

if (config.DEBUG or 'test' in sys.argv or 'pytest' not in sys.modules) and config.MEDIA_URL:
    # Ensure media files are shown properly when using a dev server
    urlpatterns += [
        re_path(r'^' + config.MEDIA_URL.lstrip('/') + '(?P<path>.*)$', static.serve, {
            'document_root': config.MEDIA_ROOT
        }),
    ]
