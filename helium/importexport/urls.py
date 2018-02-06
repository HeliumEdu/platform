from django.conf.urls import url

from helium.importexport.views import importexport_import, importexport_export

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

urlpatterns = [
    # Import/Export URLs
    url(r'^importexport/import$', importexport_import, name='importexport_import'),
    url(r'^importexport/export$', importexport_export, name='importexport_export'),
]
