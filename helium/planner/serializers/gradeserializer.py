import logging

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

logger = logging.getLogger(__name__)


class HomeworkSeriesItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    start = serializers.DateTimeField()
    category_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    points_possible = serializers.FloatField(allow_null=True)
    graded = serializers.BooleanField()
    homework_grade = serializers.FloatField(allow_null=True)
    cumulative_grade = serializers.FloatField(allow_null=True)
    impact_score = serializers.FloatField(allow_null=True)


@extend_schema_serializer(exclude_fields=['grade_points'])
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
    homework_series = HomeworkSeriesItemSerializer(many=True, required=False)


@extend_schema_serializer(exclude_fields=['grade_points'], component_name='GradeHolder')
class GradeCategorySerializer(GradeHolderSerializer):
    points_earned = serializers.FloatField(
        help_text='Total points earned across the category\'s graded assignments (completed, with a grade).')
    points_possible = serializers.FloatField(
        help_text='Total points possible across the same assignments; `points_earned / points_possible` is the '
                  'category\'s average grade.')


class GradeCourseSerializer(GradeHolderSerializer):
    points_earned = serializers.FloatField(
        help_text='Total points earned across the class\'s graded assignments (completed, with a grade).')
    points_possible = serializers.FloatField(
        help_text='Total points possible across the same assignments; `points_earned / points_possible` is the '
                  'points-based class grade.')
    categories = GradeCategorySerializer(many=True)


class GradeCourseGroupSerializer(GradeHolderSerializer):
    courses = GradeCourseSerializer(many=True)


class GradeSerializer(serializers.Serializer):
    course_groups = GradeCourseGroupSerializer(many=True)
