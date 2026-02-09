__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import re_path, path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from helium.common.admin import admin_site
from helium.common.views.apis.infoviews import InfoResourceView

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
    path(r'status/', include('health_check.urls')),
    path('info/', InfoResourceView.as_view({'get': 'info'}), name='resource_info'),
]
