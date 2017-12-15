"""
Authenticated views for User interaction.
"""

import logging

from django.contrib.auth import update_session_auth_hash
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.auth.forms.userdeleteform import UserDeleteForm
from helium.auth.forms.userpasswordchangeform import UserPasswordChangeForm
from helium.auth.serializers.userserializer import UserSerializer
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserApiListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        serializer = UserSerializer(request.user)

        return Response(serializer.data)

    def put(self, request, format=None):
        # Process password change (if present) first, as we're going to use a form-based mechanism to do (this allows us
        # to use Django's built-in auth functionality for this, and we obviously never want to serializer passwords)
        data = {}
        errors = {}
        if 'old_password' in request.data or 'new_password1' in request.data or 'new_password2' in request.data:
            form = UserPasswordChangeForm(user=request.user, data=request.data)

            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)

                logger.info('Password updated for {}'.format(request.user.get_username()))
            else:
                errors.update(list(form.errors.items()))

        # Process remaining attributes (if any) using serializers
        if 'username' in request.data and 'email' in request.data:
            serializer = UserSerializer(request.user, data=request.data, context={'request': request})

            if serializer.is_valid():
                serializer.save()

                logger.info('Details updated for user {}'.format(request.user.get_username()))

                data.update(serializer.data)
            else:
                errors.update(serializer.errors)

        if len(errors) > 0:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        elif len(data) > 0:
            metricutils.increment(request, 'action.user.updated')

            return Response(data)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, format=None):
        form = UserDeleteForm(user=request.user, data=request.data)

        if form.is_valid():
            logger.info('User {} deleted'.format(request.user.get_username()))

            metricutils.increment(request, 'action.user.deleted')

            form.user.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(dict(list(form.errors.items())), status=status.HTTP_400_BAD_REQUEST)
