__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import re_path, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from helium.common.admin import admin_site
from helium.common.views.apis.infoviews import InfoResourceView
from helium.common.views.apis.statusviews import HealthResourceView, StatusResourceView

urlpatterns = [
    # Base URL
    re_path(r'^$', RedirectView.as_view(url='/docs'), name='home'),

    # Static redirects
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico')), name='favicon'),

    # URLs for auto-generated resources
    path('admin/', admin_site.urls, name='admin'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),

    ##############################
    # Unauthenticated URLs
    ##############################
    path('status/', StatusResourceView.as_view({'get': 'status'}), name='resource_status'),
    path('health/', HealthResourceView.as_view({'get': 'health'}), name='resource_health'),
    path('info/', InfoResourceView.as_view({'get': 'info'}), name='resource_info'),
]
