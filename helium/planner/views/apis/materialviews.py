import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.models import Material
from helium.planner.permissions import IsMaterialGroupOwner
from helium.planner.schemas import SubMaterialGroupListSchema, MaterialDetailSchema
from helium.planner.serializers.materialserializer import MaterialSerializer

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
        materials = Material.objects.for_user(user.pk)
        # We do this here because the django-filters doesn't handle ManyToMany 'in' lookups well
        if 'courses' in self.request.query_params:
            materials = materials.with_courses(self.request.query_params.getlist('courses'))
        return materials

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class MaterialGroupMaterialsApiListView(GenericAPIView, CreateModelMixin, ListModelMixin):
    """
    get:
    Return a list of all material instances for the given material group.

    post:
    Create a new material instance for the given material group.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated, IsMaterialGroupOwner)
    schema = SubMaterialGroupListSchema()

    def get_queryset(self):
        user = self.request.user
        return Material.objects.for_user(user.pk).for_material_group(self.kwargs['material_group'])

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def perform_create(self, serializer, *args, **kwargs):
        serializer.save(material_group_id=self.kwargs['material_group'])

    def post(self, request, *args, **kwargs):
        for course_id in request.data.get('courses', []):
            permissions.check_course_permission(request.user.pk, course_id)

        response = self.create(request, *args, **kwargs)

        logger.info(
            'Material {} created in MaterialGroup {} for user {}'.format(response.data['id'],
                                                                         request.data['material_group'],
                                                                         request.user.get_username()))

        metricutils.increment('action.material.created', request)

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
    permission_classes = (IsAuthenticated, IsOwner, IsMaterialGroupOwner)
    schema = MaterialDetailSchema()

    def get_queryset(self):
        user = self.request.user
        return Material.objects.for_user(user.pk).for_material_group(self.kwargs['material_group'])

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if 'material_group' in request.data:
            permissions.check_material_group_permission(request.user.pk, request.data['material_group'])
        for course_id in request.data.get('courses', []):
            permissions.check_course_permission(request.user.pk, course_id)

        response = self.update(request, *args, **kwargs)

        logger.info('Material {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.material.updated', request)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'Material {} deleted from MaterialGroup {} for user {}'.format(kwargs['pk'], kwargs['material_group'],
                                                                           request.user.get_username()))

        metricutils.increment('action.material.deleted', request)

        return response
