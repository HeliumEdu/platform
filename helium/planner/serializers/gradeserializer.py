import logging

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.planner.serializers.gradescaleserializer import GradeScaleBandSerializer

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
    gpa = serializers.FloatField(
        allow_null=True,
        help_text='In a group\'s series, the group\'s `gpa` as of this graded assignment, or `-1` when no class with '
                  'credits is graded yet or the group has no grade scale. Null on ungraded assignments, and in class '
                  'and category series.')


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
    homework_series = HomeworkSeriesItemSerializer(many=True, required=False)


@extend_schema_serializer(component_name='GradeHolder')
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
    credits = serializers.DecimalField(4, 2, coerce_to_string=False,
                                       help_text='The class\'s weight in its group\'s `gpa`.')
    grade_point = serializers.DecimalField(
        5, 2, coerce_to_string=False,
        help_text='The grade point `overall_grade` earns on the class\'s `grade_scale`, or `-1` when ungraded or '
                  'the group has no grade scale.')
    grade_scale_template = serializers.IntegerField(
        allow_null=True,
        help_text='The class\'s preset grade scale, or null when it uses the group\'s `grade_scale`.')
    grade_scale = GradeScaleBandSerializer(
        many=True,
        help_text='The bands that turn the class\'s grade into its `grade_point`: its preset\'s, else the group\'s.')
    categories = GradeCategorySerializer(many=True)


class GradeCourseGroupSerializer(GradeHolderSerializer):
    gpa = serializers.DecimalField(
        7, 4, coerce_to_string=False,
        help_text='The credit-weighted mean of the classes\' `grade_point`, or `-1` with no grade scale or no '
                  'graded class with credits.')
    grade_scale = GradeScaleBandSerializer(many=True)
    in_cumulative_gpa = serializers.BooleanField(
        help_text='Whether the group\'s classes count toward `cumulative_gpa`.')
    example_schedule = serializers.BooleanField(
        help_text='Whether the group is part of the example schedule.')
    courses = GradeCourseSerializer(many=True)


class GradeSerializer(serializers.Serializer):
    course_groups = GradeCourseGroupSerializer(many=True)
    cumulative_gpa = serializers.DecimalField(
        7, 4, coerce_to_string=False,
        help_text='The credit-weighted GPA across every group outside the example schedule on the same grade scale '
                  'as the most recent group with one, plus the user\'s `prior_credits` at `prior_gpa` from their '
                  'settings, or `-1` when no such group exists, or none has a graded class with credits and there are '
                  'no prior credits.')


class NeededGradeTargetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()


class NeededGradeAssignmentSerializer(NeededGradeTargetSerializer):
    points_possible = serializers.FloatField()
    needed_points = serializers.FloatField(help_text='The points needed on this assignment.')


class NeededGradeSerializer(serializers.Serializer):
    state = serializers.ChoiceField(
        choices=['achievable', 'above_target', 'unachievable', 'target_category_has_no_weight', 'gpa_unreachable'],
        help_text='`achievable`: the desired grade can be reached. `above_target`: the class is already there. '
                  '`unachievable`: it would take more than 100%. `target_category_has_no_weight`: the category '
                  'doesn\'t count toward the class grade. '
                  '`gpa_unreachable`: even the top band of the class\'s grade scale can\'t bring the term GPA to '
                  '`desired_gpa`.')
    needed_grade = serializers.FloatField(
        help_text='The percentage needed on `assignment`, or as the `category` average when there\'s no '
                  '`assignment`, with the class\'s other ungraded work at its current grade. `0` with '
                  '`target_category_has_no_weight` or `gpa_unreachable`.')
    weighted = serializers.BooleanField(help_text='Whether the class uses weighted grading.')
    category = NeededGradeTargetSerializer(allow_null=True,
                                           help_text='The category, for a class with weighted grading.')
    assignment = NeededGradeAssignmentSerializer(
        allow_null=True,
        help_text='The assignment the score is for: the chosen one, or the category\'s last ungraded assignment.')
    grade_band = GradeScaleBandSerializer(
        allow_null=True,
        help_text='With `desired_gpa`: the band of the class\'s `grade_scale` whose `min_grade` is the class grade '
                  'solved for, or its top band with `gpa_unreachable`. Null with `desired_grade`.')
