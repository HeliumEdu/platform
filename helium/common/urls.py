from django.conf.urls import url
from django.views.generic import RedirectView
from rest_framework.documentation import include_docs_urls

from helium.common.admin import admin_site
from helium.common.views.apis.infoviews import InfoResourceView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

urlpatterns = [
    # Base URL
    url(r'^$', RedirectView.as_view(url='/docs'), name='home'),

    # URLs for auto-generated resources
    url(r'^admin/', admin_site.urls, name='admin'),
    url(r'^docs/', include_docs_urls(title='Helium API Documentation'), name='docs'),

    ##############################
    # Unauthenticated URLs
    ##############################
    url(r'^common/info/$', InfoResourceView.as_view({'get': 'info'}), name='common_resource_info'),
]
