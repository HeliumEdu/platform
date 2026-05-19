__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from helium.common.utils.validators import validate_and_normalize_date_csv
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
            'exceptions', 'user',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'num_homework', 'num_homework_completed', 'num_homework_graded',)
        read_only_fields = (
            'overall_grade', 'trend', 'private_slug', 'user', 'num_days', 'num_days_completed', 'num_homework',
            'num_homework_completed', 'num_homework_graded',)

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
                        exceptions, start_date, end_date, range_label='course group date range')
                except DjangoValidationError as e:
                    raise serializers.ValidationError({'exceptions': e.message})

        return attrs
