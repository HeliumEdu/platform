__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.planner.models import Material, MaterialGroup, Course


@extend_schema_serializer(exclude_fields=('details',))
class MaterialSerializer(serializers.ModelSerializer):
    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['material_group'].queryset = MaterialGroup.objects.for_user(self.context['request'].user.pk)
            self.fields['courses'].child_relation.queryset = Course.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Material
        fields = (
            'id', 'title', 'status', 'condition', 'website', 'price', 'details', 'material_group',
            'courses', 'notes',)
        read_only_fields = ('notes',)
