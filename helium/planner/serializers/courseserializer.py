__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from helium.common.utils.validators import validate_and_normalize_date_csv
from helium.planner.models import Course, CourseGroup
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

logger = logging.getLogger(__name__)


class CourseSerializer(serializers.ModelSerializer):
    """
    A single class within a class group. One Course has at most one
    CourseSchedule, which supports per-day start/end times. See "Common
    pitfalls" in the API description for when sections of the same class
    should be modeled as separate Courses.
    """

    schedules = CourseScheduleSerializer(many=True, required=False, read_only=True)
    teacher_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True, default='')
    num_homework = serializers.SerializerMethodField()
    num_homework_completed = serializers.SerializerMethodField()
    num_homework_graded = serializers.SerializerMethodField()
    has_weighted_grading = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['course_group'].queryset = CourseGroup.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'room', 'credits', 'color', 'website', 'is_online', 'current_grade', 'trend', 'teacher_name',
            'teacher_email', 'start_date', 'end_date', 'exceptions', 'schedules', 'course_group',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'has_weighted_grading', 'num_homework', 'num_homework_completed',
            'num_homework_graded',)
        read_only_fields = (
            'course_group', 'current_grade', 'trend', 'num_days', 'num_days_completed', 'has_weighted_grading',
            'num_homework', 'num_homework_completed', 'num_homework_graded',)

    def get_num_homework(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created courses have no homework anyway)
        return getattr(obj, 'annotated_num_homework', 0)

    def get_num_homework_completed(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created courses have no homework anyway)
        return getattr(obj, 'annotated_num_homework_completed', 0)

    def get_num_homework_graded(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created courses have no homework anyway)
        return getattr(obj, 'annotated_num_homework_graded', 0)

    @extend_schema_field(serializers.BooleanField(
        help_text=(
            '`true` = weighted grading (any category has `weight > 0`); '
            '`false` = points-based grading (a simple `earned/possible` average across '
            'all assignments). Both are valid grading modes. See '
            'https://heliumedu.freshdesk.com/support/solutions/articles/159000418648'
        )))
    def get_has_weighted_grading(self, obj) -> bool:
        # Use annotated value if available, otherwise default to False
        # (avoids N+1 queries against planner_category table)
        return getattr(obj, 'annotated_has_weighted_grading', False)

    def validate_teacher_email(self, value):
        return value or ''

    def validate(self, attrs):
        start_date = attrs.get('start_date', None)
        if not start_date and self.instance:
            start_date = self.instance.start_date
        end_date = attrs.get('end_date', None)
        if not end_date and self.instance:
            end_date = self.instance.end_date

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("The 'start_date' must be before the 'end_date'")

        if 'exceptions' in attrs or 'start_date' in attrs or 'end_date' in attrs:
            exceptions = attrs.get('exceptions', None)
            if exceptions is None and self.instance:
                exceptions = self.instance.exceptions
            if exceptions:
                try:
                    attrs['exceptions'] = validate_and_normalize_date_csv(
                        exceptions, start_date, end_date, range_label='course date range')
                except DjangoValidationError as e:
                    raise serializers.ValidationError({'exceptions': e.message})

        return attrs
