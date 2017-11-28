"""
Initialize the Admin site.
"""

from django.conf import settings
from django.contrib.admin.sites import AdminSite

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class PlatformAdminSite(AdminSite):
    site_header = settings.PROJECT_NAME + ' Administration'
    site_title = site_header
    index_title = settings.PROJECT_NAME
    login_template = 'authentication/login.html'


# Instantiate the Admin site
admin_site = PlatformAdminSite()
