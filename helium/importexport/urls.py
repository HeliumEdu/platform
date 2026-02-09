__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.urls import path

from helium.importexport.views.apis.exportviews import ExportResourceView
from helium.importexport.views.apis.importviews import ImportResourceView

urlpatterns = [
    # Import/Export URLs
    path('importexport/import/', ImportResourceView.as_view({'post': 'import_data'}),
         name='importexport_import'),
    path('importexport/export/', ExportResourceView.as_view({'get': 'export_data'}),
         name='importexport_export'),

    path('importexport/import/exampleschedule/', ImportResourceView.as_view({'post': 'import_exampleschedule'}),
         name='importexport_import_exampleschedule'),
]
