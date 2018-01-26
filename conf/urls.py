import sys

from django.conf import settings as config
from django.conf.urls import include, url
from django.views import static

import helium.auth.urls
import helium.common.urls
import helium.feed.urls
import helium.planner.urls

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

handler400 = 'helium.common.views.errorviews.bad_request'
handler401 = 'helium.common.views.errorviews.unauthorized'
handler403 = 'helium.common.views.errorviews.forbidden'
handler404 = 'helium.common.views.errorviews.not_found'
handler500 = 'helium.common.views.errorviews.internal_server_error'
handler503 = 'helium.common.views.errorviews.service_unavailable'

urlpatterns = [
    # Include app-specific URL files
    url(r'^', include(helium.common.urls)),
    url(r'^', include(helium.auth.urls)),
    url(r'^', include(helium.feed.urls)),
    url(r'^', include(helium.planner.urls)),
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
