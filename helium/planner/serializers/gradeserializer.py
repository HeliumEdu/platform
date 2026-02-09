__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class GradeHolderSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    title = serializers.CharField()

    overall_grade = serializers.DecimalField(7, 4, coerce_to_string=False)

    weight = serializers.DecimalField(7, 4, coerce_to_string=False, required=False)

    color = serializers.CharField(required=False)

    grade_by_weight = serializers.DecimalField(7, 4, coerce_to_string=False, required=False)

    trend = serializers.FloatField()

    num_homework = serializers.IntegerField()

    num_homework_completed = serializers.IntegerField()

    num_homework_graded = serializers.IntegerField()

    has_weighted_grading = serializers.BooleanField(required=False)

    grade_points = serializers.ListField(required=False)


class GradeCourseSerializer(GradeHolderSerializer):
    categories = GradeHolderSerializer(many=True)


class GradeCourseGroupSerializer(GradeHolderSerializer):
    courses = GradeCourseSerializer(many=True)


class GradeSerializer(serializers.Serializer):
    course_groups = GradeCourseGroupSerializer(many=True)
