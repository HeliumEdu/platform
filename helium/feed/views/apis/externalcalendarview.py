"""
Authenticated views for ExternalCalendar interaction.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.feed.models import ExternalCalendar
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class ExternalCalendarApiListView(APIView):
    def get(self, request, format=None):
        external_calendars = ExternalCalendar.objects.filter(user__id=request.user.pk)

        serializer = ExternalCalendarSerializer(external_calendars, many=True)

        return Response(serializer.data)

    def post(self, request, format=None):
        data = {'user': request.user.pk}
        data.update(request.data)
        serializer = ExternalCalendarSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()

            logger.info('ExternalCalendar {} created for user {}'.format(serializer.instance.pk,
                                                                         request.user.get_username()))

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required, name='dispatch')
class ExternalCalendarApiDetailView(APIView):
    def get_object(self, request, pk):
        try:
            return ExternalCalendar.objects.get(pk=pk, user_id=request.user.pk)
        except ExternalCalendar.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        externalcalendar = self.get_object(request, pk)
        serializer = ExternalCalendarSerializer(externalcalendar)

        return Response(serializer.data)

    def put(self, request, pk, format=None):
        externalcalendar = self.get_object(request, pk)
        serializer = ExternalCalendarSerializer(externalcalendar, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('ExternalCalendar {} updated for user {}'.format(serializer.instance.pk,
                                                                         request.user.get_username()))

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        externalcalendar = self.get_object(request, pk)

        externalcalendar.delete()

        logger.info('ExternalCalendar {} updated for user {}'.format(externalcalendar.pk,
                                                                     request.user.get_username()))

        return Response(status=status.HTTP_204_NO_CONTENT)
