from django.conf import settings as config
from django.conf.urls import include, url
from django.contrib.sitemaps.views import sitemap
from django.views.generic import RedirectView, TemplateView
from rest_framework.documentation import include_docs_urls

from conf.sitemaps import StaticViewSitemap
from helium.common.admin import admin_site
from helium.common.views.apis.infoviews import InfoView
from helium.common.views.generalviews import *

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    # Top-level URLs
    url(r'^admin/', include(admin_site.urls)),
    url(r'^docs/', include_docs_urls(title='Helium API Documentation')),

    # Crawler shortcuts and placeholders
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain; charset=utf-8')),
    url(r'^VzapMXZuAox7zA8HT2CtStqh530\.html$', TemplateView.as_view(template_name='VzapMXZuAox7zA8HT2CtStqh530.html')),
    url(r'^favicon\.ico$', RedirectView.as_view(url=config.STATIC_URL + 'favicon.ico', permanent=True)),
    url(r'^favicon\.png$', RedirectView.as_view(url=config.STATIC_URL + 'favicon.png', permanent=True)),

    # Base URL
    url(r'^$', home, name='home'),

    # General URLs
    url(r'^support', support, name='support'),
    url(r'^terms', terms, name='terms'),
    url(r'^privacy', privacy, name='privacy'),
    url(r'^press', press, name='press'),
    url(r'^about', about, name='about'),
    url(r'^contact', contact, name='contact'),

    ##############################
    # Unauthenticated API URLs
    ##############################
    url(r'^api/common/info/$', InfoView.as_view({'get': 'info'}), name='api_common_info'),
]
