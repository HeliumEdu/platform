import logging
from json import JSONDecodeError

from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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
        try:
            for upload in request.data.getlist('file[]'):
                json_str = b''
                for chunk in upload.chunks():
                    json_str += chunk

                importservice.import_user(request, json_str.decode("utf-8"))

            return HttpResponse()
        except JSONDecodeError:
            return JsonResponse([{
                'non_field_errors': ['An uploaded file contains invalid JSON']
            }], safe=False, status=status.HTTP_400_BAD_REQUEST)
