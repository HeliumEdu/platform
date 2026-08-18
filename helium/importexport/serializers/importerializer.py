import logging

from rest_framework import serializers

from helium.importexport.services import icsimportservice

logger = logging.getLogger(__name__)


class ImportCreateSerializer(serializers.Serializer):
    """
    Multipart request body for importing a previously-exported JSON file. Exactly one file must
    be uploaded per request, sent under the `file[]` field.
    """
    file = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        help_text='A previously-exported JSON file, sent as the multipart `file[]` field. Exactly one file per request.'
    )


class ICSImportCreateSerializer(serializers.Serializer):
    """
    Multipart request body for a one-time `.ics` import. One calendar file (`file[]`) lands in a
    single target: an existing `course`, a new course in a `course_group`, or standalone Events.
    There is no multi-course bucketing — a calendar spanning several classes must be split by the
    caller (one request per target) or imported via the JSON format, which is natively multi-course.
    """
    file = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text='The `.ics` file, sent as the multipart `file[]` field. Exactly one file per request.'
    )
    target_type = serializers.ChoiceField(
        choices=icsimportservice.TARGET_TYPE_CHOICES,
        help_text="`course` (into an existing class), `new_course` (create a class in `course_group`), "
                  "or `events` (standalone Events, no class).")
    course = serializers.IntegerField(
        required=False, help_text='Existing Course id. Required when `target_type` is `course`.')
    course_group = serializers.IntegerField(
        required=False,
        help_text='Course Group the new class is created in. Required when `target_type` is `new_course`.')

    def validate(self, attrs):
        target_type = attrs.get('target_type')
        if target_type == icsimportservice.TARGET_COURSE and not attrs.get('course'):
            raise serializers.ValidationError(
                {'course': '`course` is required when `target_type` is `course`.'})
        if target_type == icsimportservice.TARGET_NEW_COURSE and not attrs.get('course_group'):
            raise serializers.ValidationError(
                {'course_group': '`course_group` is required when `target_type` is `new_course`.'})
        return attrs


class ImportSerializer(serializers.Serializer):
    external_calendars = serializers.IntegerField()

    course_groups = serializers.IntegerField()

    courses = serializers.IntegerField()

    course_schedules = serializers.IntegerField()

    categories = serializers.IntegerField()

    resource_groups = serializers.IntegerField()

    resources = serializers.IntegerField()

    events = serializers.IntegerField()

    homework = serializers.IntegerField()

    reminders = serializers.IntegerField()

    notes = serializers.IntegerField()
