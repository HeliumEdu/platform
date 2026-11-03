import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import IF_MATCH_PARAMETER, HeliumAPIView, PreconditionMixin
from helium.planner import permissions
from helium.planner.filters import ResourceFilter
from helium.planner.models import Resource
from helium.planner.permissions import IsResourceGroupOwner
from helium.planner.serializers.resourceserializer import ResourceSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.resource']
)
class UserResourcesApiListView(HeliumAPIView, ListModelMixin):
    serializer_class = ResourceSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = ResourceFilter

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            resources = Resource.objects.for_user(user.pk).select_related('resource_group').prefetch_related('courses', 'notes_set')
            # We do this here because the django-filters doesn't handle ManyToMany 'in' lookups well
            if 'courses' in self.request.query_params:
                resources = resources.with_courses(self.request.query_params.getlist('courses'))
            return resources
        else:
            return Resource.objects.none()

    @extend_schema(
        summary='List all Resources for the User',
        parameters=[
            OpenApiParameter(
                name='courses',
                type=int,
                many=True,
                description='Restrict the result to resources linked to any of the given class IDs. Repeat '
                            'the parameter to pass multiple IDs: `?courses=1&courses=2`.',
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all resource instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response


@extend_schema(
    tags=['planner.resource']
)
class ResourceGroupResourcesApiListView(HeliumAPIView, CreateModelMixin, ListModelMixin):
    serializer_class = ResourceSerializer
    permission_classes = (IsAuthenticated, IsResourceGroupOwner)
    filterset_class = ResourceFilter

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return Resource.objects.for_user(user.pk).for_resource_group(self.kwargs['resource_group']).select_related('resource_group').prefetch_related('courses', 'notes_set')
        else:
            return Resource.objects.none()

    @extend_schema(summary='List Resources in a ResourceGroup')
    def get(self, request, *args, **kwargs):
        """
        Return a list of all resource instances for the given resource group.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer, *args, **kwargs):
        serializer.save(resource_group_id=self.kwargs['resource_group'])

    @extend_schema(
        summary='Create a Resource in a ResourceGroup',
        responses={
            201: ResourceSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new resource instance for the given resource group.
        """
        courses = request.data.get('courses', [])
        if courses:
            for course_id in courses:
                permissions.check_course_permission(request.user.pk, course_id)
        for resource_group_id in permissions.requested_ids(request.data, 'resource_group'):
            permissions.check_resource_group_permission(request.user.pk, resource_group_id)

        response = self.create(request, *args, **kwargs)

        logger.info(
            f"Resource {response.data['id']} created in ResourceGroup {kwargs['resource_group']} for user {request.user.pk}")

        return response


@extend_schema(
    tags=['planner.resource']
)
class ResourceGroupResourcesApiDetailView(PreconditionMixin, HeliumAPIView, RetrieveModelMixin, UpdateModelMixin,
                                          DestroyModelMixin):
    serializer_class = ResourceSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsResourceGroupOwner)
    filterset_class = ResourceFilter

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return Resource.objects.for_user(user.pk).for_resource_group(self.kwargs['resource_group']).select_related('resource_group').prefetch_related('courses', 'notes_set')
        else:
            return Resource.objects.none()

    @extend_schema(summary='Retrieve a Resource')
    def get(self, request, *args, **kwargs):
        """
        Return the given resource instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    @extend_schema(summary='Update a Resource', parameters=[IF_MATCH_PARAMETER])
    def put(self, request, *args, **kwargs):
        """
        Update the given resource instance.
        """
        courses = request.data.get('courses', [])
        if courses:
            for course_id in courses:
                permissions.check_course_permission(request.user.pk, course_id)
        for resource_group_id in permissions.requested_ids(request.data, 'resource_group'):
            permissions.check_resource_group_permission(request.user.pk, resource_group_id)

        response = self.update(request, *args, **kwargs)

        logger.info(f"Resource {kwargs['pk']} updated for user {request.user.pk}")

        return response

    @extend_schema(
        summary='Delete a Resource',
        parameters=[IF_MATCH_PARAMETER],
        tags=['planner.resource']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given resource instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"Resource {kwargs['pk']} deleted from ResourceGroup {kwargs['resource_group']} for user {request.user.pk}")

        return response
