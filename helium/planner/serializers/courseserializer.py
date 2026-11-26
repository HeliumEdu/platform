import logging

from django.db import transaction
from django.utils.translation import gettext
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from helium.common import enums, errorcodes
from helium.common.errormessages import EXCEPTION_DATES_OUTSIDE_CLASS_MESSAGE
from helium.common.serializers.validation import validate_date_range_and_exceptions
from helium.common.utils import gradeutils
from helium.common.utils.openapiutils import support_article_url
from helium.planner.models import Category, Course, CourseGroup
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer
from helium.planner.services import categoryservice

logger = logging.getLogger(__name__)


class CourseSerializer(serializers.ModelSerializer):
    """
    A single course within a course group. A Course may have more than one
    CourseSchedule (e.g. a lecture plus a lab), each of which supports
    per-day start/end times. See "Importing a schedule from a syllabus" in
    the API description for when sections of the same course should be
    modeled as separate Courses.

    Each schedule's `recurrence_groups` carries the pre-computed, renderable
    form of that schedule (see `CourseScheduleSerializer`).
    """

    schedules = serializers.SerializerMethodField()
    template = serializers.ChoiceField(
        choices=enums.CATEGORY_TEMPLATE_CHOICES, required=False, write_only=True,
        help_text='The set of default categories to provision on the new course.')
    teacher_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True, default='')
    num_homework = serializers.SerializerMethodField()
    num_homework_completed = serializers.SerializerMethodField()
    num_homework_graded = serializers.SerializerMethodField()
    has_weighted_grading = serializers.SerializerMethodField()
    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['course_group'].queryset = CourseGroup.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'room', 'credits', 'color', 'website', 'is_online', 'current_grade', 'grade_point',
            'grade_scale_template', 'trend',
            'teacher_name', 'teacher_email', 'start_date', 'end_date', 'exceptions', 'schedules', 'template',
            'course_group', 'notes', 'created_at', 'updated_at',
            # Property fields (which should also be declared as read-only)
            'has_weighted_grading', 'num_homework', 'num_homework_completed', 'num_homework_graded',)
        read_only_fields = (
            'course_group', 'notes', 'current_grade', 'grade_point', 'trend', 'created_at', 'updated_at',
            'has_weighted_grading', 'num_homework', 'num_homework_completed', 'num_homework_graded',)

    def create(self, validated_data):
        # `None` means the field was omitted; a provided template can be `0` (a falsy enum value), so
        # test against None rather than truthiness.
        template = validated_data.pop('template', None)
        _validate_grade_scale_template(validated_data,
                                       CourseGroup.objects.filter(pk=validated_data['course_group_id'])
                                       .values_list('grade_scale', flat=True).first())

        with transaction.atomic():
            course = super().create(validated_data)

            Category.objects.get_uncategorized(course.id)
            if template is not None:
                categoryservice.seed_categories(course.id, template)

        return course

    def update(self, instance, validated_data):
        # Provisioning only applies at create time; a template on update is a no-op.
        validated_data.pop('template', None)
        _validate_grade_scale_template(validated_data, instance.course_group.grade_scale)

        return super().update(instance, validated_data)

    @extend_schema_field(CourseScheduleSerializer(many=True))
    def get_schedules(self, obj):
        schedules = sorted(obj.schedules.all(), key=lambda schedule: schedule.id)

        # These schedules belong to `obj`, so hand each its already-loaded parent course rather than
        # letting `recurrence_groups` re-fetch course/course group/owner settings per schedule.
        for schedule in schedules:
            schedule.course = obj

        return CourseScheduleSerializer(schedules, many=True, context=self.context).data

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
            'all homework). Both are valid grading modes. See '
            f"{support_article_url('grades-and-progress/setting-up-weighted-grading-assignment-categories')}"
        )))
    def get_has_weighted_grading(self, obj) -> bool:
        # Use annotated value if available, otherwise default to False
        # (avoids N+1 queries against planner_category table)
        return getattr(obj, 'annotated_has_weighted_grading', False)

    def validate_teacher_email(self, value):
        return value or ''

    def validate(self, attrs):
        validate_date_range_and_exceptions(attrs, self.instance, EXCEPTION_DATES_OUTSIDE_CLASS_MESSAGE)

        return attrs


def _validate_grade_scale_template(validated_data, group_grade_scale):
    template = validated_data.get('grade_scale_template')
    if template is None or gradeutils.is_compatible_preset(template, group_grade_scale):
        return

    compatible = [enums.GRADE_SCALE_TEMPLATES[preset]['label']
                  for preset in gradeutils.compatible_presets(group_grade_scale)]
    if compatible:
        message = gettext("Doesn't fit the group's grade scale: a class's preset can only award grades the group's "
                          'scale does. Compatible presets: %(presets)s.') % {'presets': ', '.join(compatible)}
    else:
        message = gettext("Doesn't fit the group's grade scale: a class's preset can only award grades the group's "
                          'scale does. The group has no grade scale.')
    raise serializers.ValidationError({'grade_scale_template': message},
                                      code=errorcodes.GRADE_SCALE_TEMPLATE_INCOMPATIBLE)
