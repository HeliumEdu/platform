from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.planner.models import Resource, ResourceGroup, Course


@extend_schema_serializer(component_name='Resource')
class ResourceSerializer(serializers.ModelSerializer):
    resource_group = serializers.PrimaryKeyRelatedField(required=False,
                                                        queryset=ResourceGroup.objects.all(),
                                                        help_text='The resource group with which to associate.')

    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['resource_group'].queryset = ResourceGroup.objects.for_user(self.context['request'].user.pk)
            self.fields['courses'].child_relation.queryset = Course.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Resource
        fields = (
            'id', 'title', 'status', 'condition', 'website', 'price', 'resource_group',
            'courses', 'notes', 'created_at', 'updated_at',)
        read_only_fields = ('notes', 'created_at', 'updated_at',)
