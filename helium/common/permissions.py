import logging

from rest_framework import permissions

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.get_user() == request.user
