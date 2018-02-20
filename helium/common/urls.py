from django.conf.urls import include, url
from rest_framework.documentation import include_docs_urls

from helium.common.admin import admin_site
from helium.common.views.apis.infoviews import InfoView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.8'

urlpatterns = [
    # Top-level URLs
    url(r'^admin/', include(admin_site.urls)),
    url(r'^docs/', include_docs_urls(title='Helium API Documentation')),

    ##############################
    # Unauthenticated URLs
    ##############################
    url(r'^api/common/info/$', InfoView.as_view({'get': 'info'}), name='api_common_info'),
]
