import logging

from django.db import models as django_models
from rest_framework import serializers

from helium.common import enums
from helium.common.serializers.fields import ExceptionDatesField, TzAwareDateTimeField
from helium.common.serializers.validation import validate_start_before_end
from helium.common.utils.openapiutils import help_text_with_support_article
from helium.common.utils.validators import validate_recurrence_rule
from helium.planner.models import Homework, Category, Resource, Course
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.services import recurrenceservice
from helium.planner.tasks import recalculate_category_grade

logger = logging.getLogger(__name__)


class HomeworkSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        django_models.DateTimeField: TzAwareDateTimeField,
    }

    resources = serializers.PrimaryKeyRelatedField(many=True, required=False,
                                                   queryset=Resource.objects.all(),
                                                   help_text='A list of resources with which to associate.')

    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)

    course_group = serializers.IntegerField(source='course.course_group_id', read_only=True)

    exception_dates = ExceptionDatesField(required=False, allow_null=True,
                                          help_text=Homework._meta.get_field('exception_dates').help_text)

    calendar_item_type = serializers.ChoiceField(choices=enums.CALENDAR_ITEM_TYPE_CHOICES, read_only=True,
                                                 help_text='Which kind of calendar item this is; a client can key rendering off it without inspecting the URL it came from.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['category'].queryset = Category.objects.for_user(self.context['request'].user.pk)
            self.fields['course'].queryset = Course.objects.for_user(self.context['request'].user.pk)
            # ManyToMany fields need to have their `child_relation` queryset modified instead
            self.fields['resources'].child_relation.queryset = Resource.objects.for_user(
                self.context['request'].user.pk)

    class Meta:
        model = Homework
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority',
            'current_grade', 'completed', 'completed_at', 'category', 'resources', 'attachments',
            'reminders', 'notes', 'course', 'course_group', 'recurrence_rule', 'exception_dates', 'created_at',
            'updated_at',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'notes', 'calendar_item_type', 'completed_at', 'created_at',
                            'updated_at',)
        extra_kwargs = {
            'recurrence_rule': {
                'validators': [validate_recurrence_rule],
                'help_text': 'iCal RRULE string (e.g. `FREQ=WEEKLY;BYDAY=MO,WE,FR`) that repeats it from `start`, or '
                             'null. Without `COUNT` or `UNTIL`, it repeats through the class\'s `end_date`. A '
                             'repeating Homework isn\'t completed or graded itself; complete each occurrence '
                             'with `scope=this`.',
            },
            'current_grade': {
                'help_text': help_text_with_support_article(
                    Homework, 'current_grade', 'grades-and-progress/how-helium-calculates-your-grades'),
            },
            'completed': {
                'help_text': help_text_with_support_article(
                    Homework, 'completed', 'grades-and-progress/setting-up-weighted-grading-assignment-categories'),
            },
        }

    def validate(self, attrs):
        validate_start_before_end(attrs, self.instance)
        self._validate_category_in_course(attrs)

        rule = attrs.get('recurrence_rule', getattr(self.instance, 'recurrence_rule', None))
        completed = attrs.get('completed', getattr(self.instance, 'completed', False))
        grade = attrs.get('current_grade', getattr(self.instance, 'current_grade', enums.UNGRADED))
        if rule and (completed or grade != enums.UNGRADED):
            raise serializers.ValidationError(
                "A repeating Homework isn't completed or graded itself; complete or grade an occurrence with "
                "`scope=this`.")

        return attrs

    def create(self, validated_data):
        course = validated_data.get('course') or Course.objects.get(pk=validated_data['course_id'])
        recurrenceservice.prepare_write(validated_data, course.get_user())
        if validated_data.get('recurrence_rule'):
            validated_data['recurrence_rule'] = recurrenceservice.bound_to_course(
                validated_data['recurrence_rule'], validated_data['start'], validated_data['end'],
                validated_data.get('all_day', False), course)

        return super().create(validated_data)

    def _validate_category_in_course(self, attrs):
        if 'course' not in attrs and 'category' not in attrs:
            return

        category = attrs['category'] if 'category' in attrs else getattr(self.instance, 'category', None)
        if category is None:
            return

        if self.instance:
            course_id = attrs['course'].pk if 'course' in attrs else self.instance.course_id
        else:
            request = self.context.get('request')
            url_kwargs = (request.parser_context or {}).get('kwargs', {}) if request else {}
            course_id = url_kwargs.get('course') or (attrs['course'].pk if attrs.get('course') else None)

        if course_id is not None and category.course_id != int(course_id):
            raise serializers.ValidationError({'category': "The 'category' must belong to the same class."})

    def update(self, instance, validated_data):
        recurrenceservice.prepare_write(validated_data, instance.get_user(), instance)
        if validated_data.get('recurrence_rule'):
            validated_data['recurrence_rule'] = recurrenceservice.bound_to_course(
                validated_data['recurrence_rule'], validated_data.get('start', instance.start),
                validated_data.get('end', instance.end), validated_data.get('all_day', instance.all_day),
                validated_data.get('course', instance.course))

        old_category = self.instance.category if 'category' in validated_data and self.instance.category_id != \
                                                                                  validated_data['category'] else None

        instance = super().update(instance, validated_data)

        if old_category:
            moved_course = old_category.course_id != instance.course_id
            recalculate_category_grade(old_category.pk, recalculate_course=moved_course)

        return instance


class HomeworkExtendedSerializer(HomeworkSerializer):
    attachments = AttachmentSerializer(many=True)
    reminders = ReminderSerializer(many=True)
