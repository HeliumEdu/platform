import logging

from rest_framework import serializers

from helium.common.serializers.validation import validate_date_range_and_exceptions
from helium.planner.models import CourseGroup

logger = logging.getLogger(__name__)


class CourseGroupSerializer(serializers.ModelSerializer):
    """
    A group of classes within a given timeframe (typically a semester or
    quarter). `overall_grade` is a flat average of member classes. See
    https://www.heliumedu.com/support/classes/setting-up-and-managing-classes.
    For full-term imports, see also "Bulk import" in the API description.
    """

    num_homework = serializers.SerializerMethodField()
    num_homework_completed = serializers.SerializerMethodField()
    num_homework_graded = serializers.SerializerMethodField()

    class Meta:
        model = CourseGroup
        fields = (
            'id', 'title', 'start_date', 'end_date', 'shown_on_calendar', 'overall_grade', 'trend', 'private_slug',
            'exceptions', 'user', 'created_at', 'updated_at',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'num_homework', 'num_homework_completed', 'num_homework_graded',)
        read_only_fields = (
            'overall_grade', 'trend', 'private_slug', 'user', 'created_at', 'updated_at', 'num_days',
            'num_days_completed', 'num_homework', 'num_homework_completed', 'num_homework_graded',)

    def get_num_homework(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created course groups have no homework anyway)
        return getattr(obj, 'annotated_num_homework', 0)

    def get_num_homework_completed(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created course groups have no homework anyway)
        return getattr(obj, 'annotated_num_homework_completed', 0)

    def get_num_homework_graded(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created course groups have no homework anyway)
        return getattr(obj, 'annotated_num_homework_graded', 0)

    def validate(self, attrs):
        validate_date_range_and_exceptions(attrs, self.instance, 'group date range')

        return attrs
