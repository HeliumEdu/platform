import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.importexport.services import importservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class ImportView(APIView):
    """
    post:
    Import the resources for the authenticated user from the the uploaded files. Multiple files can be imported at once
    passed in the `file[]` field.

    Each model will be imported in a schema matching that of the documented APIs.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = self.request.user

        for upload in request.data.getlist('file[]'):
            json_str = b''
            for chunk in upload.chunks():
                json_str += chunk

            importservice.import_user(user, json_str.decode("utf-8"))

        return HttpResponse()
