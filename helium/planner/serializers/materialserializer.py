import logging

from rest_framework import serializers

from helium.planner.models import Material, MaterialGroup, Course

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

logger = logging.getLogger(__name__)


class MaterialSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['material_group'].queryset = MaterialGroup.objects.for_user(self.context['request'].user.pk)
            # ManyToMany fields need to have their `child_relation` queryset modified instead
            self.fields['courses'].child_relation.queryset = Course.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Material
        fields = (
            'id', 'title', 'status', 'condition', 'website', 'price', 'details', 'material_group',
            'courses')
