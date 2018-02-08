from django.conf.urls import url

from helium.importexport.views.exportviews import ExportView
from helium.importexport.views.importviews import ImportView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

urlpatterns = [
    # Import/Export URLs
    url(r'^api/importexport/import/$', ImportView.as_view(), name='importexport_import'),
    url(r'^api/importexport/export/$', ExportView.as_view(), name='importexport_export'),
]
