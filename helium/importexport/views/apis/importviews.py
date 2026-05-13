__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
import logging

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.common.services import uploadfileservice
from helium.common.views.base import HeliumAPIView
from helium.importexport.serializers.importerializer import ImportCreateSerializer, ImportSerializer
from helium.importexport.services import importservice
from helium.planner.services import reminderservice

logger = logging.getLogger(__name__)


class ImportResourceView(ViewSet, HeliumAPIView):
    serializer_class = ImportSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    @extend_schema(
        request=ImportCreateSerializer,
        responses={200: ImportSerializer},
        examples=[
            OpenApiExample(
                'bulk_syllabus_import',
                media_type='multipart/form-data',
                summary='Export-shaped JSON for a single-term import (one file per request)',
                description=(
                    'The body of the `file[]` multipart field. Exactly one file must be uploaded '
                    'per request; submitting zero or more than one file returns `400`. Matches the '
                    '`Export` component schema (the shape returned by `GET /importexport/export/`) '
                    '— same top-level keys, same per-row fields. Relationships are expressed as '
                    'integer `id` values that resolve within the file: a CourseGroup `id` is '
                    "referenced by each Course's `course_group`; a Course `id` is referenced by "
                    'its CourseSchedule, Categories, and Homework rows; a Category `id` is '
                    'referenced by each Homework. `id` values only need to be unique and stable '
                    'within the file; the importer assigns fresh database `id` values on insert. '
                    'All datetimes are tz-aware ISO-8601.'
                ),
                value={
                    'external_calendars': [],
                    'course_groups': [
                        {
                            'id': 1,
                            'title': 'Fall 2026',
                            'start_date': '2026-09-02',
                            'end_date': '2026-12-13',
                            'shown_on_calendar': True,
                            'exceptions': '',
                        },
                    ],
                    'courses': [
                        {
                            'id': 10,
                            'title': 'BIO 151 — Lecture',
                            'room': 'Bagley 131',
                            'credits': '3.00',
                            'color': '#4986e7',
                            'website': 'https://canvas.example.edu/bio-151',
                            'is_online': False,
                            'teacher_name': 'Dr. Jane Smith',
                            'teacher_email': 'jsmith@example.edu',
                            'start_date': '2026-09-02',
                            'end_date': '2026-12-13',
                            'exceptions': '',
                            'course_group': 1,
                        },
                        {
                            'id': 11,
                            'title': 'BIO 151 — Lab',
                            'room': 'Bagley 312',
                            'credits': '1.00',
                            'color': '#4986e7',
                            'is_online': False,
                            'teacher_name': 'Dr. Jane Smith',
                            'teacher_email': 'jsmith@example.edu',
                            'start_date': '2026-09-02',
                            'end_date': '2026-12-13',
                            'exceptions': '',
                            'course_group': 1,
                        },
                    ],
                    'course_schedules': [
                        {
                            'id': 100,
                            'days_of_week': '0101010',
                            'sun_start_time': '00:00:00', 'sun_end_time': '00:00:00',
                            'mon_start_time': '10:00:00', 'mon_end_time': '10:50:00',
                            'tue_start_time': '00:00:00', 'tue_end_time': '00:00:00',
                            'wed_start_time': '10:00:00', 'wed_end_time': '10:50:00',
                            'thu_start_time': '00:00:00', 'thu_end_time': '00:00:00',
                            'fri_start_time': '10:00:00', 'fri_end_time': '10:50:00',
                            'sat_start_time': '00:00:00', 'sat_end_time': '00:00:00',
                            'course': 10,
                        },
                        {
                            'id': 101,
                            'days_of_week': '0000100',
                            'sun_start_time': '00:00:00', 'sun_end_time': '00:00:00',
                            'mon_start_time': '00:00:00', 'mon_end_time': '00:00:00',
                            'tue_start_time': '00:00:00', 'tue_end_time': '00:00:00',
                            'wed_start_time': '00:00:00', 'wed_end_time': '00:00:00',
                            'thu_start_time': '13:30:00', 'thu_end_time': '16:20:00',
                            'fri_start_time': '00:00:00', 'fri_end_time': '00:00:00',
                            'sat_start_time': '00:00:00', 'sat_end_time': '00:00:00',
                            'course': 11,
                        },
                    ],
                    'categories': [
                        {'id': 200, 'title': 'Homework', 'weight': '20.00',
                         'color': '#16a765', 'course': 10},
                        {'id': 201, 'title': 'Exams', 'weight': '50.00',
                         'color': '#cd74e6', 'course': 10},
                        {'id': 202, 'title': 'Participation', 'weight': '30.00',
                         'color': '#fad165', 'course': 10},
                        {'id': 203, 'title': 'Lab Reports', 'weight': '100.00',
                         'color': '#16a765', 'course': 11},
                    ],
                    'resource_groups': [],
                    'resources': [],
                    'events': [],
                    'homework': [
                        {
                            'id': 300,
                            'title': 'Problem Set 1',
                            'all_day': False,
                            'show_end_time': False,
                            'start': '2026-09-14T23:59:00-07:00',
                            'end': '2026-09-14T23:59:00-07:00',
                            'priority': 50,
                            'current_grade': '-1/100',
                            'completed': False,
                            'category': 200,
                            'materials': [],
                            'course': 10,
                        },
                        {
                            'id': 301,
                            'title': 'Midterm Exam',
                            'all_day': False,
                            'show_end_time': True,
                            'start': '2026-10-14T10:00:00-07:00',
                            'end': '2026-10-14T11:30:00-07:00',
                            'priority': 80,
                            'current_grade': '-1/100',
                            'completed': False,
                            'category': 201,
                            'materials': [],
                            'course': 10,
                        },
                        {
                            'id': 310,
                            'title': 'Lab 1 Report',
                            'all_day': False,
                            'show_end_time': False,
                            'start': '2026-09-17T23:59:00-07:00',
                            'end': '2026-09-17T23:59:00-07:00',
                            'priority': 50,
                            'current_grade': '-1/100',
                            'completed': False,
                            'category': 203,
                            'materials': [],
                            'course': 11,
                        },
                    ],
                    'reminders': [],
                    'notes': [],
                },
                request_only=True,
            ),
        ],
    )
    def import_data(self, request, *args, **kwargs):
        """
        Import the resources for the authenticated user from the uploaded file. Exactly one file must be uploaded per
        request in the `file[]` field; submitting zero or more than one file returns `400`.

        The file may not exceed the `max_upload_size` (bytes) returned by `GET /info/`.

        Each model will be imported in a schema matching that of the documented APIs.
        """
        uploads = request.data.getlist('file[]')
        if len(uploads) != 1:
            logger.warning(f'Rejected import request from user {request.user.pk} with {len(uploads)} files.')
            raise ValidationError({
                'details': 'Upload exactly one file per request.'
            })

        external_calendar_count = 0
        course_groups_count = 0
        courses_count = 0
        course_schedules_count = 0
        categories_count = 0
        resource_groups_count = 0
        resources_count = 0
        events_count = 0
        homework_count = 0
        reminders_count = 0
        notes_count = 0

        for upload in uploads:
            try:
                json_str = uploadfileservice.read(upload).decode('utf-8')
                data = json.loads(json_str)

                if isinstance(data, list):
                    raise ValidationError({
                        'details': f'Invalid JSON structure: {upload}.'
                    })

                (external_calendar_count_file, course_groups_count_file, courses_count_file,
                 course_schedules_count_file, categories_count_file, resource_groups_count_file, resources_count_file,
                 events_count_file, homework_count_file, reminders_count_file,
                 notes_count_file) = importservice.import_user(request, data)

                reminderservice.process_push_reminders(True)

                external_calendar_count += external_calendar_count_file
                course_groups_count += course_groups_count_file
                courses_count += courses_count_file
                course_schedules_count += course_schedules_count_file
                categories_count += categories_count_file
                resource_groups_count += resource_groups_count_file
                resources_count += resources_count_file
                events_count += events_count_file
                homework_count += homework_count_file
                reminders_count += reminders_count_file
                notes_count += notes_count_file
            except ValueError:
                raise ValidationError({
                    'details': f'Invalid JSON in file: {upload}.'
                })

        serializer = ImportSerializer({
            'external_calendars': external_calendar_count,
            'course_groups': course_groups_count,
            'courses': courses_count,
            'course_schedules': course_schedules_count,
            'categories': categories_count,
            'resource_groups': resource_groups_count,
            'resources': resources_count,
            'events': events_count,
            'homework': homework_count,
            'reminders': reminders_count,
            'notes': notes_count,
        })

        return Response(serializer.data)

    @extend_schema(exclude=True)
    def import_exampleschedule(self, request, *args, **kwargs):
        importservice.import_example_schedule(request.user)

        # Re-show the Getting Started dialog so users can explore and clear the example data
        request.user.settings.show_getting_started = True
        request.user.settings.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
