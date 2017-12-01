"""
Authenticated views for UserProfile interaction.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.users.serializers.userprofileserializer import UserProfileSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class UserProfileApiView(APIView):
    def get(self, request, format=None):
        serializer = UserProfileSerializer(request.user.profile)

        return Response(serializer.data)

    def put(self, request, format=None):
        serializer = UserProfileSerializer(request.user.profile, data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
