__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

import logging

from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.filters import MaterialGroupFilter
from helium.planner.models import MaterialGroup
from helium.planner.serializers.materialgroupserializer import MaterialGroupSerializer

logger = logging.getLogger(__name__)


class MaterialGroupsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = MaterialGroupSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = MaterialGroupFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.material_groups.all()
        else:
            return MaterialGroup.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all material group instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        """
        Create a new material group instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"MaterialGroup {response.data['id']} created for user {request.user.get_username()}")

        return response


class MaterialGroupsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = MaterialGroupSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    filterset_class = MaterialGroupFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.material_groups.all()
        else:
            return MaterialGroup.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given material group instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given material group instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"MaterialGroup {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given material group instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"MaterialGroup {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
