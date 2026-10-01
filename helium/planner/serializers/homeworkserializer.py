import logging

from django.db import models as django_models
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.common import enums
from helium.common.serializers.fields import TzAwareDateTimeField
from helium.common.serializers.validation import validate_start_before_end
from helium.planner.models import Homework, Category, Material, Course
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.tasks import recalculate_category_grade

logger = logging.getLogger(__name__)


#: Legacy 'comments' parameter, can be removed once all clients are reporting >= 3.10.0.
#: Legacy 'materials' parameter, can be removed once all clients are reporting >= 3.9.4.
@extend_schema_serializer(exclude_fields=('comments', 'materials'))
class HomeworkSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        django_models.DateTimeField: TzAwareDateTimeField,
    }

    #: Once all backend code has been factored from Material terminology to Resource terminology, including data model changes and migrations, this line can be removed.
    resources = serializers.PrimaryKeyRelatedField(source='materials', many=True, required=False,
                                                   queryset=Material.objects.all(),
                                                   help_text='A list of resources with which to associate.')

    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)

    course_group = serializers.IntegerField(source='course.course_group_id', read_only=True)

    calendar_item_type = serializers.ChoiceField(choices=enums.CALENDAR_ITEM_TYPE_CHOICES, read_only=True,
                                                 help_text='Which kind of calendar item this is; a client can key rendering off it without inspecting the URL it came from.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['category'].queryset = Category.objects.for_user(self.context['request'].user.pk)
            self.fields['course'].queryset = Course.objects.for_user(self.context['request'].user.pk)
            # ManyToMany fields need to have their `child_relation` queryset modified instead
            #: Legacy parameter, can be removed once all clients are reporting >= 3.9.4.
            for resources_field in ('resources', 'materials'):
                self.fields[resources_field].child_relation.queryset = Material.objects.for_user(
                    self.context['request'].user.pk)

    class Meta:
        model = Homework
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'comments',
            'current_grade', 'completed', 'completed_at', 'category', 'materials', 'resources', 'attachments',
            'reminders', 'notes', 'course', 'course_group',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'notes', 'calendar_item_type', 'completed_at',)

    def validate(self, attrs):
        validate_start_before_end(attrs, self.instance)
        self._validate_category_in_course(attrs)

        return attrs

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
        old_category = self.instance.category if 'category' in validated_data and self.instance.category_id != \
                                                                                  validated_data['category'] else None

        instance = super().update(instance, validated_data)

        if old_category:
            moved_course = old_category.course_id != instance.course_id
            recalculate_category_grade(old_category.pk, recalculate_course=moved_course)

        return instance


#: Legacy 'comments' parameter, can be removed once all clients are reporting >= 3.10.0.
#: Legacy 'materials' parameter, can be removed once all clients are reporting >= 3.9.4.
@extend_schema_serializer(exclude_fields=('comments', 'materials'))
class HomeworkExtendedSerializer(HomeworkSerializer):
    attachments = AttachmentSerializer(many=True)
    reminders = ReminderSerializer(many=True)
