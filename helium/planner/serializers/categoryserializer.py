import logging

from rest_framework import serializers

from helium.planner.models.category import Category

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            'id', 'title', 'weight', 'average_grade', 'grade_by_weight', 'trend', 'color', 'course',)
        read_only_fields = ('average_grade', 'grade_by_weight', 'trend', 'course',)

    def validate_weight(self, weight):
        """
        Validate the weight of the incoming Category, ensuring it doesn't cause the parent course's cumulative
        weights to exceed 100.

        :param weight: the weight to be validated
        """
        course_id = self.context['request'].parser_context['kwargs']['course']

        weight_total = 0
        for category in Category.objects.filter(course_id=course_id).iterator():
            weight_total += category.weight

        if weight_total + weight > 100:
            raise serializers.ValidationError(
                "The cumulative weights of all categories associated with a course cannot exceed 100.")

        return weight
