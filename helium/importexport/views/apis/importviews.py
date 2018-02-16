import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet

from helium.common.services import uploadfileservice
from helium.common.utils import metricutils
from helium.importexport.services import importservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class ImportView(ViewSet):
    """
    import_data:
    Import the resources for the authenticated user from the the uploaded files. Multiple files can be imported at once
    passed in the `file[]` field.

    The maximum file size for each upload is 10M.

    Each model will be imported in a schema matching that of the documented APIs.
    """
    permission_classes = (IsAuthenticated,)

    def import_data(self, request, *args, **kwargs):
        for upload in request.data.getlist('file[]'):
            json_str = uploadfileservice.read(upload)

            importservice.import_user(request, json_str.decode("utf-8"))

            metricutils.increment('action.user.imported', request)

            return HttpResponse()
