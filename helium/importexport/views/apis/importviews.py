__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.27"

import json
import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.common.services import uploadfileservice
from helium.common.views.base import HeliumAPIView
from helium.importexport.serializers.importerializer import ImportSerializer
from helium.importexport.services import importservice
from helium.planner.services import reminderservice

logger = logging.getLogger(__name__)


class ImportResourceView(ViewSet, HeliumAPIView):
    serializer_class = ImportSerializer
    permission_classes = (IsAuthenticated,)

    def import_data(self, request, *args, **kwargs):
        """
        Import the resources for the authenticated user from the uploaded files. Multiple files can be imported at
        once passed in the `file[]` field.

        The maximum file size for each upload is 10M.

        Each model will be imported in a schema matching that of the documented APIs.
        """
        external_calendar_count = 0
        course_groups_count = 0
        courses_count = 0
        course_schedules_count = 0
        categories_count = 0
        material_groups_count = 0
        materials_count = 0
        events_count = 0
        homework_count = 0
        reminders_count = 0

        for upload in request.data.getlist('file[]'):
            try:
                json_str = uploadfileservice.read(upload).decode('utf-8')
                data = json.loads(json_str)

                if isinstance(data, list):
                    raise ValidationError({
                        'details': f'Invalid JSON structure: {upload}.'
                    })

                (external_calendar_count_file, course_groups_count_file, courses_count_file,
                 course_schedules_count_file, categories_count_file, material_groups_count_file, materials_count_file,
                 events_count_file, homework_count_file, reminders_count_file) = importservice.import_user(request,
                                                                                                           data)

                reminderservice.process_push_reminders(True)

                external_calendar_count += external_calendar_count_file
                course_groups_count += course_groups_count_file
                courses_count += courses_count_file
                course_schedules_count += course_schedules_count_file
                categories_count += categories_count_file
                material_groups_count += material_groups_count_file
                materials_count += materials_count_file
                events_count += events_count_file
                homework_count += homework_count_file
                reminders_count += reminders_count_file
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
            'material_groups': material_groups_count,
            'materials': materials_count,
            'events': events_count,
            'homework': homework_count,
            'reminders': reminders_count
        })

        return Response(serializer.data)

    def import_exampleschedule(self, request, *args, **kwargs):
        importservice.import_example_schedule(request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)
