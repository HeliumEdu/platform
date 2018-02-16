from django.conf.urls import url

from helium.importexport.views.apis.exportviews import ExportView
from helium.importexport.views.apis.importviews import ImportView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

urlpatterns = [
    # Import/Export URLs
    url(r'^api/importexport/import/$', ImportView.as_view({'post': 'import_data'}), name='importexport_import'),
    url(r'^api/importexport/export/$', ExportView.as_view({'get': 'export_data'}), name='importexport_export'),
]
