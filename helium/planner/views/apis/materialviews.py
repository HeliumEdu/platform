__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

import logging

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner import permissions
from helium.planner.filters import MaterialFilter
from helium.planner.models import Material
from helium.planner.permissions import IsMaterialGroupOwner
from helium.planner.serializers.materialserializer import MaterialSerializer

logger = logging.getLogger(__name__)


class UserMaterialsApiListView(HeliumAPIView, ListModelMixin):
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = MaterialFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            materials = Material.objects.for_user(user.pk)
            # We do this here because the django-filters doesn't handle ManyToMany 'in' lookups well
            if 'courses' in self.request.query_params:
                materials = materials.with_courses(self.request.query_params.getlist('courses'))
            return materials
        else:
            return Material.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all material instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response


class MaterialGroupMaterialsApiListView(HeliumAPIView, CreateModelMixin, ListModelMixin):
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated, IsMaterialGroupOwner)
    filterset_class = MaterialFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Material.objects.for_user(user.pk).for_material_group(self.kwargs['material_group'])
        else:
            return Material.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all material instances for the given material group.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer, *args, **kwargs):
        serializer.save(material_group_id=self.kwargs['material_group'])

    def post(self, request, *args, **kwargs):
        """
        Create a new material instance for the given material group.
        """
        for course_id in request.data.get('courses', []):
            permissions.check_course_permission(request.user.pk, course_id)

        response = self.create(request, *args, **kwargs)

        logger.info(
            f"Material {response.data['id']} created in MaterialGroup {request.data['material_group']} for user {request.user.get_username()}")

        return response


class MaterialGroupMaterialsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsMaterialGroupOwner)
    filterset_class = MaterialFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Material.objects.for_user(user.pk).for_material_group(self.kwargs['material_group'])
        else:
            return Material.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given material instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given material instance.
        """
        if 'material_group' in request.data:
            permissions.check_material_group_permission(request.user.pk, request.data['material_group'])
        for course_id in request.data.get('courses', []):
            permissions.check_course_permission(request.user.pk, course_id)

        response = self.update(request, *args, **kwargs)

        logger.info(f"Material {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given material instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"Material {kwargs['pk']} deleted from MaterialGroup {kwargs['material_group']} for user {request.user.get_username()}")

        return response
