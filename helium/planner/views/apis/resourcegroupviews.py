import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import IF_MATCH_PARAMETER, HeliumAPIView, PreconditionMixin
from helium.planner.filters import ResourceGroupFilter
from helium.planner.models import ResourceGroup
from helium.planner.serializers.resourcegroupserializer import ResourceGroupSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.resourcegroup']
)
class ResourceGroupsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = ResourceGroupSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = ResourceGroupFilter

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return user.resource_groups.all()
        else:
            return ResourceGroup.objects.none()

    @extend_schema(
        summary='List ResourceGroups for the User',
        tags=['planner.resourcegroup']
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all resource group instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary='Create a ResourceGroup',
        responses={
            201: ResourceGroupSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new resource group instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"ResourceGroup {response.data['id']} created for user {request.user.pk}")

        return response


@extend_schema(
    tags=['planner.resourcegroup']
)
class ResourceGroupsApiDetailView(PreconditionMixin, HeliumAPIView, RetrieveModelMixin, UpdateModelMixin,
                                  DestroyModelMixin):
    serializer_class = ResourceGroupSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    filterset_class = ResourceGroupFilter

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return user.resource_groups.all()
        else:
            return ResourceGroup.objects.none()

    @extend_schema(summary='Retrieve a ResourceGroup')
    def get(self, request, *args, **kwargs):
        """
        Return the given resource group instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    @extend_schema(summary='Update a ResourceGroup', parameters=[IF_MATCH_PARAMETER])
    def put(self, request, *args, **kwargs):
        """
        Update the given resource group instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"ResourceGroup {kwargs['pk']} updated for user {request.user.pk}")

        return response

    @extend_schema(
        summary='Delete a ResourceGroup',
        parameters=[IF_MATCH_PARAMETER],
        tags=['planner.resourcegroup']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given resource group instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"ResourceGroup {kwargs['pk']} deleted for user {request.user.pk}")

        return response
