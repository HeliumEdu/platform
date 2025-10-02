__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

from django.urls import path

from helium.importexport.views.apis.exportviews import ExportResourceView
from helium.importexport.views.apis.importviews import ImportResourceView

urlpatterns = [
    # Import/Export URLs
    path('importexport/import/', ImportResourceView.as_view({'post': 'import_data'}),
         name='importexport_resource_import'),
    path('importexport/export/', ExportResourceView.as_view({'get': 'export_data'}),
         name='importexport_resource_export'),
]
