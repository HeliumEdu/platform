"""
Permissions for interacting with the REST API.
"""
import logging

from rest_framework import permissions

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


# TODO: refactor CourseGroup and Course permissions (for example, see categoryviews.py and others) to utilize this permissions system

class IsOwner(permissions.BasePermission):
    """
    This permission can be for any model that implements get_user() to retrieve the owning User of the object.
    """

    def has_object_permission(self, request, view, obj):
        return obj.get_user() == request.user
