import logging
import random

from rest_framework import serializers

from helium.common import enums
from helium.planner.models.category import Category

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.4'

logger = logging.getLogger(__name__)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            'id', 'title', 'weight', 'average_grade', 'grade_by_weight', 'trend', 'color', 'course',
            # Property fields (which should also be declared as read-only)
            'num_homework', 'num_homework_graded',)
        read_only_fields = (
            'average_grade', 'grade_by_weight', 'trend', 'course', 'num_homework', 'num_homework_graded',)

    def validate_weight(self, weight):
        """
        Validate the weight of the incoming Category, ensuring it doesn't cause the parent course's cumulative
        weights to exceed 100.

        :param weight: the weight to be validated
        """
        course_id = self.context['request'].parser_context['kwargs']['course']

        weight_total = 0
        for category in Category.objects.for_course(course_id).iterator():
            if self.instance and category.pk == self.instance.pk:
                continue

            weight_total += category.weight

        if weight_total + weight > 100:
            raise serializers.ValidationError(
                "The cumulative weights of all categories associated with a course cannot exceed 100.")

        return weight

    def create(self, validated_data):
        if 'color' not in validated_data:
            validated_data['color'] = random.choice(enums.ALLOWED_COLORS)[0]

        return super().create(validated_data)
