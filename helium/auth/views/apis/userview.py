"""
Authenticated views for User interaction.
"""

import logging

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.auth.forms.userdeleteform import UserDeleteForm
from helium.auth.forms.userpasswordchangeform import UserPasswordChangeForm
from helium.auth.serializers.userserializer import UserSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class UserApiView(APIView):
    def get(self, request, format=None):
        serializer = UserSerializer(request.user)

        return Response(serializer.data)

    def put(self, request, format=None):
        # Process password change (if present) first, as we're going to use a form-based mechanism to do (this allows us
        # to use Django's built-in auth functionality for this, and we obviously never want to serializer passwords)
        errors = {}
        if 'old_password' in request.data or 'new_password1' in request.data or 'new_password2' in request.data:
            form = UserPasswordChangeForm(user=request.user, data=request.data)

            if form.is_valid():
                # print user_password_form
                form.save()
                update_session_auth_hash(request, form.user)

                logger.info('Password updated for {}'.format(request.user.get_username()))
            else:
                errors.update(form.errors.items())

        # Process remaining attributes (if any) using serializers
        if 'username' in request.data and 'email' in request.data:
            serializer = UserSerializer(request.user, data=request.data, context={'request': request})

            if serializer.is_valid():
                serializer.save()

                logger.info('Details updated for user {}'.format(request.user.get_username()))

                return Response(serializer.data)
            else:
                errors.update(serializer.errors)
        elif len(errors) == 0:
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, format=None):
        form = UserDeleteForm(user=request.user, data=request.data)

        if form.is_valid():
            form.user.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(dict(form.errors.items()), status=status.HTTP_400_BAD_REQUEST)
