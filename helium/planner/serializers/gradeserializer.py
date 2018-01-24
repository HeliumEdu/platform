import logging

from rest_framework import serializers

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class GradeHolderSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    title = serializers.CharField()

    overall_grade = serializers.DecimalField(7, 4, coerce_to_string=False)

    trend = serializers.FloatField()

    grade_points = serializers.ListField()


class GradeCourseSerializer(GradeHolderSerializer):
    categories = GradeHolderSerializer(many=True)


class GradeCourseGroupSerializer(GradeHolderSerializer):
    courses = GradeCourseSerializer(many=True)


class GradeSerializer(serializers.Serializer):
    course_groups = GradeCourseGroupSerializer(many=True)
