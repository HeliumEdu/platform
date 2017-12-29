"""
Authenticated views for Material interaction.
"""

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.common.utils import metricutils
from helium.planner.models import MaterialGroup, Material, Course
from helium.planner.permissions import IsOwner
from helium.planner.serializers.materialserializer import MaterialSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserMaterialsApiListView(GenericAPIView, ListModelMixin):
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Material.objects.filter(material_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class MaterialGroupMaterialsApiListView(APIView):
    permission_classes = (IsAuthenticated,)

    def check_material_group_permission(self, request, material_group_id):
        if not MaterialGroup.objects.filter(pk=material_group_id).exists():
            raise NotFound('MaterialGroup not found.')
        if not MaterialGroup.objects.filter(pk=material_group_id, user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id).exists():
            raise NotFound('Course not found.')
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get(self, request, material_group_id, format=None):
        self.check_material_group_permission(request, material_group_id)

        materials = Material.objects.filter(material_group_id=material_group_id,
                                            material_group__user_id=request.user.pk)

        serializer = MaterialSerializer(materials, many=True)

        return Response(serializer.data)

    def post(self, request, material_group_id, format=None):
        data = request.data.copy()

        self.check_material_group_permission(request, material_group_id)
        if 'courses' in data:
            course_ids = str(data['courses']).split(',')
            data['courses'] = []
            for course_id in course_ids:
                data['courses'].append(course_id)
                self.check_course_permission(request, course_id)
        else:
            data['courses'] = []

        serializer = MaterialSerializer(data=data)

        if serializer.is_valid():
            serializer.save(material_group_id=material_group_id)

            logger.info(
                'Material {} created in MaterialGroup {} for user {}'.format(serializer.instance.pk, material_group_id,
                                                                             self.request.user.get_username()))

            metricutils.increment(request, 'action.material.created')

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MaterialGroupMaterialsApiDetailView(APIView):
    permission_classes = (IsAuthenticated, IsOwner,)

    def check_material_group_permission(self, request, material_group_id):
        if not MaterialGroup.objects.filter(pk=material_group_id).exists():
            raise NotFound('MaterialGroup not found.')
        if not MaterialGroup.objects.filter(pk=material_group_id, user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id).exists():
            raise NotFound('Course not found.')
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get_object(self, request, material_group_id, pk):
        try:
            return Material.objects.get(material_group_id=material_group_id, pk=pk)
        except Material.DoesNotExist:
            raise Http404

    def get(self, request, material_group_id, pk, format=None):
        material = self.get_object(request, material_group_id, pk)
        self.check_object_permissions(request, material)

        serializer = MaterialSerializer(material)

        return Response(serializer.data)

    def put(self, request, material_group_id, pk, format=None):
        data = request.data.copy()

        material = self.get_object(request, material_group_id, pk)
        self.check_object_permissions(request, material)
        if 'material_group' in data:
            self.check_material_group_permission(request, data['material_group'])
        if 'courses' in data:
            course_ids = str(data['courses']).split(',')
            data['courses'] = []
            for course_id in course_ids:
                data['courses'].append(course_id)
                self.check_course_permission(request, course_id)
        else:
            data['courses'] = []

        serializer = MaterialSerializer(material, data=data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Material {} updated for user {}'.format(pk, self.request.user.get_username()))

            metricutils.increment(request, 'action.material.updated')

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, material_group_id, pk, format=None):
        material = self.get_object(request, material_group_id, pk)
        self.check_object_permissions(request, material)

        material.delete()

        logger.info('Material {} deleted from MaterialGroup {} for user {}'.format(pk, material_group_id,
                                                                                   self.request.user.get_username()))

        metricutils.increment(request, 'action.material.deleted')

        return Response(status=status.HTTP_204_NO_CONTENT)
