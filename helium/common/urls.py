from django.urls import re_path, path
from django.views.generic import RedirectView
from rest_framework.documentation import include_docs_urls

from helium.common.admin import admin_site
from helium.common.views.apis.healthviews import HealthResourceView
from helium.common.views.apis.infoviews import InfoResourceView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.9'

urlpatterns = [
    # Base URL
    re_path(r'^$', RedirectView.as_view(url='/docs'), name='home'),

    # URLs for auto-generated resources
    path('admin/', admin_site.urls, name='admin'),
    path('docs/', include_docs_urls(title='Helium API Documentation'), name='docs'),

    ##############################
    # Unauthenticated URLs
    ##############################
    path('health/', HealthResourceView.as_view({'get': 'health'}), name='resource_health'),
    path('info/', InfoResourceView.as_view({'get': 'info'}), name='resource_info'),
]
