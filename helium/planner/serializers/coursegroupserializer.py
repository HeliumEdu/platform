"""
CourseGroup serializer.
"""
import logging

from rest_framework import serializers

from helium.planner.models import CourseGroup

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseGroup
        fields = ('id', 'title', 'start_date', 'end_date', 'shown_on_calendar', 'average_grade', 'trend', 'private_slug', 'user',)
        read_only_fields = ('average_grade', 'trend', 'private_slug', 'user',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user

        return super(CourseGroupSerializer, self).create(validated_data)
