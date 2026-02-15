__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

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
            'repeating', 'homework', 'event', 'course', 'user',)
        read_only_fields = ('start_of_range', 'user',)

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

        # Validate that repeating is only allowed for course reminders
        is_repeating = attrs.get('repeating', False) or (self.instance and self.instance.repeating and 'repeating' not in attrs)
        if is_repeating and not final_has_course:
            raise serializers.ValidationError("The `repeating` field can only be set to true for course reminders.")

        # We're setting these to None here as the serialization save will persist the new parent
        if self.instance and ('event' in attrs or 'homework' in attrs or 'course' in attrs):
            self.instance.event = None
            self.instance.homework = None
            self.instance.course = None

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
        representation['user'] = instance.user.id

        return representation
