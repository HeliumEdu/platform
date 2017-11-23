"""
Sitemaps URLs.
"""

from django.contrib import sitemaps
from django.core.urlresolvers import reverse

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['home', 'login', 'forgot', 'register', 'about']

    def location(self, item):
        return reverse(item)
