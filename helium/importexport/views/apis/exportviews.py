__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import ViewSet

from helium.common.views.base import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.importexport.serializers.exportserializer import ExportSerializer
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, MaterialGroup, Material, Event, \
    Homework, Reminder, Note

logger = logging.getLogger(__name__)


class ExportResourceView(ViewSet, HeliumAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = ExportSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(summary='Export all User data as JSON')
    def export_data(self, request, *args, **kwargs):
        """
        Return an export of all non-sensitive data for the authenticated account. The response sets
        `Content-Disposition` to `attachment; filename=Helium_<email-local-part>_<YYYY-MM-DD>.json`
        (the local-part is the segment of the account email before `@`), so a browser will save it
        as a dated download.

        The exported data for each model type will match that of the documented APIs.
        """
        user = self.request.user

        serializer = ExportSerializer({
            'external_calendars': ExternalCalendar.objects.for_user(user.pk),
            'course_groups': CourseGroup.objects.for_user(user.pk).annotate(
                annotated_num_homework=Count('courses__homework', distinct=True),
                annotated_num_homework_completed=Count('courses__homework', filter=Q(courses__homework__completed=True), distinct=True),
                annotated_num_homework_graded=Count('courses__homework', filter=Q(courses__homework__completed=True) & ~Q(courses__homework__current_grade='-1/100'), distinct=True),
            ),
            'courses': Course.objects.for_user(user.pk).annotate(
                annotated_num_homework=Count('homework', distinct=True),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True), distinct=True),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'), distinct=True),
                annotated_has_weighted_grading=Exists(Category.objects.filter(course_id=OuterRef('pk'), weight__gt=0)),
            ),
            'course_schedules': CourseSchedule.objects.for_user(user.pk),
            'categories': Category.objects.for_user(user.pk).annotate(
                annotated_num_homework=Count('homework'),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True)),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100')),
            ),
            'resource_groups': MaterialGroup.objects.for_user(user.pk),
            'resources': Material.objects.for_user(user.pk),
            'events': Event.objects.for_user(user.pk),
            'homework': Homework.objects.for_user(user.pk),
            'reminders': Reminder.objects.for_user(user.pk),
            'notes': Note.objects.for_user(user.pk).prefetch_related('homework', 'events', 'resources'),
        })

        json_str = JSONRenderer().render(serializer.data)

        email_local = user.email.split('@')[0] if user.email else 'backup'
        filename = f"Helium_{email_local}_{datetime.now().strftime('%Y-%m-%d')}.json"

        response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
        response['Filename'] = filename
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
