"""
Unauthenticated error views.
"""

import logging

from django.shortcuts import render
from rest_framework import status

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def bad_request(request):
    return render(request, "errors/400.html", status=status.HTTP_400_BAD_REQUEST)


def unauthorized(request):
    return render(request, "errors/401.html", status=status.HTTP_401_UNAUTHORIZED)


def forbidden(request):
    return render(request, "errors/403.html", status=status.HTTP_403_FORBIDDEN)


def not_found(request):
    return render(request, "errors/404.html", status=status.HTTP_404_NOT_FOUND)


def internal_server_error(request):
    return render(request, "errors/500.html", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def service_unavailable(request):
    return render(request, "errors/503.html", status=status.HTTP_503_SERVICE_UNAVAILABLE)
