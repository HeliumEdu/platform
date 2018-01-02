import json
import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.models import Material
from helium.planner.serializers.materialserializer import MaterialSerializer
from helium.planner.views.apis.schemas.materialgroupschemas import SubMaterialGroupListSchema
from helium.planner.views.apis.schemas.materialschemas import MaterialDetailSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserMaterialsApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all material instances for the authenticated user.
    """
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Material.objects.filter(material_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class MaterialGroupMaterialsApiListView(GenericAPIView, CreateModelMixin, ListModelMixin):
    """
    get:
    Return a list of all material instances for the given material group.

    post:
    Create a new material instance for the given material group.
    """
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated,)
    schema = SubMaterialGroupListSchema()

    courses = []

    def get_queryset(self):
        user = self.request.user
        return Material.objects.filter(material_group_id=self.kwargs['material_group'],
                                       material_group__user_id=user.pk)

    def get_serializer(self, *args, **kwargs):
        serializer = super(MaterialGroupMaterialsApiListView, self).get_serializer(*args, **kwargs)

        if isinstance(serializer, MaterialSerializer):
            serializer.set_course_id_values(self.courses)

        return serializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        request.POST._mutable = True
        request.data['material_group'] = kwargs['material_group']
        # If Django Rest Framework adds better support for properly setting ManyToMany relationships, this can be
        # removed
        if 'courses' in request.data:
            self.courses = json.loads(request.data['courses'])
            request.data.pop('courses')
        request.POST._mutable = False

        permissions.check_material_group_permission(request, request.data['material_group'])
        for course_id in self.courses:
            permissions.check_course_permission(request, course_id)

        response = self.create(request, *args, **kwargs)

        logger.info(
            'Material {} created in MaterialGroup {} for user {}'.format(response.data['id'],
                                                                         request.data['material_group'],
                                                                         request.user.get_username()))

        metricutils.increment(request, 'action.material.created')

        return response


class MaterialGroupMaterialsApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given material instance.

    put:
    Update the given material instance.

    delete:
    Delete the given material instance.
    """
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = MaterialDetailSchema()

    courses = []

    def get_queryset(self):
        user = self.request.user
        return Material.objects.filter(material_group_id=self.kwargs['material_group'],
                                       material_group__user_id=user.pk)

    def get_serializer(self, *args, **kwargs):
        serializer = super(MaterialGroupMaterialsApiDetailView, self).get_serializer(*args, **kwargs)

        if isinstance(serializer, MaterialSerializer):
            serializer.set_course_id_values(self.courses)

        return serializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        request.POST._mutable = True
        # If Django Rest Framework adds better support for properly setting ManyToMany relationships, this can be
        # removed
        if 'courses' in request.data:
            self.courses = json.loads(request.data['courses'])
            request.data.pop('courses')
        request.POST._mutable = False

        if 'material_group' in request.data:
            permissions.check_material_group_permission(request, request.data['material_group'])
        for course_id in self.courses:
            permissions.check_course_permission(request, course_id)

        response = self.update(request, *args, **kwargs)

        logger.info('Material {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.material.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'Material {} deleted from MaterialGroup {} for user {}'.format(kwargs['pk'], kwargs['material_group'],
                                                                           request.user.get_username()))

        metricutils.increment(request, 'action.material.deleted')

        return response
