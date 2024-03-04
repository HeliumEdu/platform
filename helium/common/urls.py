__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from django.urls import re_path, path
from django.views.generic import RedirectView
from rest_framework.documentation import include_docs_urls

from helium.common.admin import admin_site
from helium.common.views.apis.infoviews import InfoResourceView
from helium.common.views.apis.statusviews import HealthResourceView, StatusResourceView

urlpatterns = [
    # Base URL
    re_path(r'^$', RedirectView.as_view(url='/docs'), name='home'),

    # URLs for auto-generated resources
    path('admin/', admin_site.urls, name='admin'),
    path('docs/', include_docs_urls(title='Helium API Documentation'), name='docs'),

    ##############################
    # Unauthenticated URLs
    ##############################
    path('status/', StatusResourceView.as_view({'get': 'status'}), name='resource_status'),
    path('health/', HealthResourceView.as_view({'get': 'health'}), name='resource_health'),
    path('info/', InfoResourceView.as_view({'get': 'info'}), name='resource_info'),
]
