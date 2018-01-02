import logging

from rest_framework import serializers

from helium.planner.models import Material

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class MaterialSerializer(serializers.ModelSerializer):
    course_id_values = []

    class Meta:
        model = Material
        fields = (
            'id', 'title', 'status', 'condition', 'website', 'price', 'details', 'seller_details', 'material_group',
            'courses')

    def set_course_id_values(self, courses):
        self.course_id_values = courses

    def update_course_relations(self, instance):
        instance.courses = self.course_id_values
        instance.save()

    def create(self, validated_data):
        # This value is given to us by the Django Rest Framework's underlying ListSerializer, but it doesn't properly
        # set ManyToMany relationships. Thus, we pop it off and set the relationship it ourselves
        if 'courses' in validated_data:
            validated_data.pop('courses')

        material = Material.objects.create(**validated_data)

        self.update_course_relations(material)

        return material

    def update(self, instance, validated_data):
        # This value is given to us by the Django Rest Framework's underlying ListSerializer, but it doesn't properly
        # set ManyToMany relationships. Thus, we pop it off and set the relationship it ourselves
        if 'courses' in validated_data:
            validated_data.pop('courses')

        super(MaterialSerializer, self).update(instance, validated_data)

        self.update_course_relations(instance)

        return instance
