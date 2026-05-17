__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import timedelta

from rest_framework import serializers

from helium.common import enums
from helium.planner.models import Reminder, Homework, Event, Course

logger = logging.getLogger(__name__)


class ReminderSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['homework'].queryset = Homework.objects.for_user(self.context['request'].user.pk)
            self.fields['event'].queryset = Event.objects.for_user(self.context['request'].user.pk)
            self.fields['course'].queryset = Course.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Reminder
        fields = (
            'id', 'title', 'message', 'start_of_range', 'offset', 'offset_type', 'type', 'sent', 'dismissed',
            'homework', 'event', 'course', 'user',)
        # `start_of_range` is derived state — the model's `save()` always recomputes it from
        # parent + offset, so accepting it on the write API would be misleading.
        read_only_fields = ('user', 'start_of_range',)

    def validate(self, attrs):
        # Check what's being explicitly set in this request
        event_in_request = attrs.get('event', None)
        homework_in_request = attrs.get('homework', None)
        course_in_request = attrs.get('course', None)

        # Count how many are being set in this request
        request_set_count = sum([bool(event_in_request), bool(homework_in_request), bool(course_in_request)])

        # For new instances, require exactly one parent
        if not self.instance and request_set_count == 0:
            raise serializers.ValidationError("One of `event`, `homework`, or `course` must be given.")

        # Don't allow multiple parents to be set in the same request
        if request_set_count > 1:
            raise serializers.ValidationError("Only one of `event`, `homework`, or `course` may be given.")

        # Determine what the final parent will be after this update
        # If a new parent is being set, it replaces any existing one
        if request_set_count > 0:
            final_has_course = bool(course_in_request)
        else:
            # No new parent in request, keep existing
            final_has_course = self.instance and self.instance.course

        # Capture original parent refs before nulling them out below, for the sent-reset check.
        orig_homework = self.instance.homework if self.instance else None
        orig_event = self.instance.event if self.instance else None
        orig_course = self.instance.course if self.instance else None

        # We're setting these to None here as the serialization save will persist the new parent
        if self.instance and ('event' in attrs or 'homework' in attrs or 'course' in attrs):
            self.instance.event = None
            self.instance.homework = None
            self.instance.course = None

        # Recompute start_of_range when the parent or offset changes, or on create
        parent_changed = 'homework' in attrs or 'event' in attrs or 'course' in attrs
        offset_changed = 'offset' in attrs or 'offset_type' in attrs
        if not self.instance or parent_changed or offset_changed:
            homework = attrs.get('homework') or (self.instance and self.instance.homework)
            event = attrs.get('event') or (self.instance and self.instance.event)
            course = attrs.get('course') or (self.instance and self.instance.course)
            offset = attrs.get('offset', getattr(self.instance, 'offset', None))
            offset_type = attrs.get('offset_type', getattr(self.instance, 'offset_type', None))
            offset_delta = timedelta(**{enums.REMINDER_OFFSET_TYPE_CHOICES[offset_type][1]: int(offset)})

            if homework:
                attrs['start_of_range'] = homework.start - offset_delta
            elif event:
                attrs['start_of_range'] = event.start - offset_delta
            elif course:
                temp = Reminder(course=course, offset=offset, offset_type=offset_type)
                next_start = temp._get_next_course_occurrence_start()
                if next_start:
                    attrs['start_of_range'] = next_start - offset_delta
                else:
                    attrs['start_of_range'] = None

        # On update, only reset sent when offset or parent actually changed — not just because
        # they appear in a full PUT payload.
        if self.instance and self.instance.sent and 'start_of_range' in attrs:
            offset_changed = (
                ('offset' in attrs and attrs['offset'] != self.instance.offset) or
                ('offset_type' in attrs and attrs['offset_type'] != self.instance.offset_type)
            )
            parent_changed = (
                ('homework' in attrs and attrs.get('homework') != orig_homework) or
                ('event' in attrs and attrs.get('event') != orig_event) or
                ('course' in attrs and attrs.get('course') != orig_course)
            )
            if offset_changed or parent_changed:
                if Reminder.should_reset_sent(attrs.get('start_of_range')):
                    attrs['sent'] = False

        return attrs


class ReminderExtendedSerializer(ReminderSerializer):
    def to_representation(self, instance):
        # Import serializers here to avoid circular imports
        from helium.planner.serializers.homeworkserializer import HomeworkSerializer
        from helium.planner.serializers.eventserializer import EventSerializer
        from helium.planner.serializers.courseserializer import CourseSerializer
        from helium.planner.serializers.categoryserializer import CategorySerializer

        # Get base representation first
        representation = super().to_representation(instance)

        # Serialize homework and event with their respective serializers if present
        if instance.homework:
            homework_serializer = HomeworkSerializer(instance.homework, context=self.context)
            homework_data = homework_serializer.data
            # Nest the course and category objects to maintain depth=2 behavior
            if instance.homework.course:
                course_serializer = CourseSerializer(instance.homework.course, context=self.context)
                homework_data['course'] = course_serializer.data
            if instance.homework.category:
                category_serializer = CategorySerializer(instance.homework.category, context=self.context)
                homework_data['category'] = category_serializer.data
            representation['homework'] = homework_data

        if instance.event:
            event_serializer = EventSerializer(instance.event, context=self.context)
            representation['event'] = event_serializer.data

        if instance.course:
            course_serializer = CourseSerializer(instance.course, context=self.context)
            representation['course'] = course_serializer.data

        # Keep only the user ID instead of the full nested user object
        representation['user'] = instance.user_id

        return representation
