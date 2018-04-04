from django.urls import path

from helium.importexport.views.apis.exportviews import ExportResourceView
from helium.importexport.views.apis.importviews import ImportResourceView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.6'

urlpatterns = [
    # Import/Export URLs
    path('importexport/import/', ImportResourceView.as_view({'post': 'import_data'}),
         name='importexport_resource_import'),
    path('importexport/export/', ExportResourceView.as_view({'get': 'export_data'}),
         name='importexport_resource_export'),
]
