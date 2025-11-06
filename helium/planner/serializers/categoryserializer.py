__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.16.0"

import logging

from rest_framework import serializers

from helium.planner.models.category import Category

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

    def validate_title(self, title):
        """
        Ensure the title is unique within the course.

        :param title: the title to be validated
        """
        if self.instance:
            pk = self.instance.pk
        else:
            pk = None
        course_id = self.context['request'].parser_context['kwargs']['course']

        if Category.objects.for_course(course_id).exclude(pk=pk).filter(title=title):
            raise serializers.ValidationError(f"This course already has a category named \"{title}\".")

        return title

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
