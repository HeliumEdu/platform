"""
Category serializer.
"""
import logging

from rest_framework import serializers

from helium.planner.models.category import Category

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            'id', 'title', 'weight', 'average_grade', 'grade_by_weight', 'trend', 'color', 'course',)
        read_only_fields = ('average_grade', 'trend', 'course',)
