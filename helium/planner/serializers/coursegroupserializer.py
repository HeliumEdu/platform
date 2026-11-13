import logging

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.common import enums
from helium.common.serializers.validation import validate_date_range_and_exceptions
from helium.common.utils import gradeutils
from helium.common.utils.openapiutils import support_article_url
from helium.planner.models import CourseGroup
from helium.planner.serializers.gradescaleserializer import GradeScaleField
from helium.planner.services import gradingservice

logger = logging.getLogger(__name__)


@extend_schema_serializer(description=(
    'A group of classes within a given timeframe (typically a semester or quarter). `overall_grade` is a flat '
    f"average of member classes. See {support_article_url('classes/setting-up-and-managing-classes')}. For "
    'full-term imports, see also "Bulk import" in the API description.'
))
class CourseGroupSerializer(serializers.ModelSerializer):

    num_homework = serializers.SerializerMethodField()
    num_homework_completed = serializers.SerializerMethodField()
    num_homework_graded = serializers.SerializerMethodField()
    grade_scale = GradeScaleField(
        required=False,
        help_text='The bands that map a class grade to a grade point: none for no grade scale, or 2 to 20 in '
                  'ascending `min_grade` order from `0`, whose `grade_point` values only rise or only fall. When '
                  'omitted on create, it is filled from `grade_scale_template`, else copied from the most recent '
                  'group outside the example schedule, else empty.')
    grade_scale_template = serializers.ChoiceField(
        choices=enums.GRADE_SCALE_TEMPLATE_CHOICES, required=False, allow_null=True,
        help_text='A preset grade scale, sent instead of `grade_scale`. If both are sent, `grade_scale` must match '
                  'the preset. In responses, the preset `grade_scale` matches, or null for a custom scale.')

    class Meta:
        model = CourseGroup
        fields = (
            'id', 'title', 'start_date', 'end_date', 'shown_on_calendar', 'overall_grade', 'trend', 'grade_scale',
            'grade_scale_template', 'gpa', 'exceptions', 'example_schedule', 'user', 'created_at', 'updated_at',
            # Property fields (which should also be declared as read-only)
            'num_homework', 'num_homework_completed', 'num_homework_graded',)
        read_only_fields = (
            'overall_grade', 'trend', 'gpa', 'example_schedule', 'user', 'created_at', 'updated_at', 'num_homework',
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
        validate_date_range_and_exceptions(attrs, self.instance, 'group date range')

        template = attrs.pop('grade_scale_template', None)
        if template is not None:
            if 'grade_scale' not in attrs:
                attrs['grade_scale'] = gradeutils.preset_grade_scale(template)
            elif gradeutils.preset_for(attrs['grade_scale']) != template:
                raise serializers.ValidationError(
                    {'grade_scale_template': "Doesn't match 'grade_scale'. Send one or the other, or values that "
                                             "match the preset."})

        return attrs

    def create(self, validated_data):
        if 'grade_scale' not in validated_data:
            validated_data['grade_scale'] = _inherited_grade_scale(validated_data['user'])

        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.refresh_from_db(fields=['gpa'])

        return instance


def _inherited_grade_scale(user):
    most_recent = gradingservice.most_recent_course_group(
        CourseGroup.objects.for_user(user.pk).filter(example_schedule=False).values('id', 'start_date', 'grade_scale'))

    return gradeutils.default_grade_scale() if most_recent is None else most_recent['grade_scale']
