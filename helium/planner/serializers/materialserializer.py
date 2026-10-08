from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.planner.models import Material, MaterialGroup, Course


#: Legacy 'details' parameter, can be removed once all clients are reporting >= 3.10.0.
#: Once all backend code has been factored from Material terminology to Resource terminology, including data model changes and migrations, this line can be removed.
@extend_schema_serializer(exclude_fields=('details',), component_name='Resource')
class MaterialSerializer(serializers.ModelSerializer):
    #: Once all backend code has been factored from Material terminology to Resource terminology, including data model changes and migrations, this line can be removed.
    resource_group = serializers.PrimaryKeyRelatedField(source='material_group', required=False,
                                                        queryset=MaterialGroup.objects.all(),
                                                        help_text='The resource group with which to associate.')

    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['resource_group'].queryset = MaterialGroup.objects.for_user(self.context['request'].user.pk)
            self.fields['courses'].child_relation.queryset = Course.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Material
        fields = (
            'id', 'title', 'status', 'condition', 'website', 'price', 'details', 'resource_group',
            'courses', 'notes', 'created_at', 'updated_at',)
        read_only_fields = ('notes', 'created_at', 'updated_at',)
