__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet

from helium.auth.serializers.userserializer import UserSerializer
from helium.common.services import uploadfileservice
from helium.common.views.views import HeliumAPIView
from helium.importexport.services import importservice

logger = logging.getLogger(__name__)


class ImportResourceView(ViewSet, HeliumAPIView):
    """
    import_data:
    Import the resources for the authenticated user from the the uploaded files. Multiple files can be imported at once
    passed in the `file[]` field.

    The maximum file size for each upload is 10M.

    Each model will be imported in a schema matching that of the documented APIs.
    """
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def import_data(self, request, *args, **kwargs):
        for upload in request.data.getlist('file[]'):
            json_str = uploadfileservice.read(upload).decode('utf-8')

            importservice.import_user(request, json_str)

        return HttpResponse()
