import logging

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import ViewSet

from helium.common import enums, errorcodes
from helium.common.views.base import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.feed.services import feedservice
from helium.importexport.serializers.exportserializer import ExportSerializer
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, ResourceGroup, Resource, Event, \
    Homework, Reminder, Note

logger = logging.getLogger(__name__)


_ICS_EXPORTS = {
    'events': feedservice.events_feed,
    'homework': feedservice.homework_feed,
    'courseschedules': feedservice.courseschedules_feed,
    'all': feedservice.all_feed,
}


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
                annotated_num_homework_graded=Count('courses__homework', filter=Q(courses__homework__completed=True) & ~Q(courses__homework__current_grade=enums.UNGRADED), distinct=True),
            ),
            'courses': Course.objects.for_user(user.pk).annotate(
                annotated_num_homework=Count('homework', distinct=True),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True), distinct=True),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade=enums.UNGRADED), distinct=True),
                annotated_has_weighted_grading=Exists(Category.objects.filter(course_id=OuterRef('pk'), weight__gt=0)),
            ).prefetch_related('notes_set'),
            'course_schedules': CourseSchedule.objects.for_user(user.pk),
            'categories': Category.objects.for_user(user.pk).annotate(
                annotated_num_homework=Count('homework'),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True)),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade=enums.UNGRADED)),
            ),
            'resource_groups': ResourceGroup.objects.for_user(user.pk),
            'resources': Resource.objects.for_user(user.pk),
            'events': Event.objects.for_user(user.pk),
            'homework': Homework.objects.for_user(user.pk),
            'reminders': Reminder.objects.for_user(user.pk),
            'notes': Note.objects.for_user(user.pk).prefetch_related('homework', 'events', 'resources', 'courses'),
        })

        json_str = JSONRenderer().render(serializer.data)

        return _download_response(user, json_str, 'application/json; charset=utf-8', 'json')

    @extend_schema(
        summary='Export the User\'s calendar as ICS',
        parameters=[
            OpenApiParameter('calendar', enum=list(_ICS_EXPORTS), default='all',
                             description='The calendar to export (`homework` is Assignments, `courseschedules` is '
                                         'Class Schedules), or `all` for all three in one file.'),
        ],
        responses={
            (200, 'text/calendar'): OpenApiResponse(
                response=OpenApiTypes.STR,
                description='The calendar, in iCalendar format.'
            )
        }
    )
    def export_ics_data(self, request, *args, **kwargs):
        """
        Return a one-time export of the authenticated account's calendar (`text/calendar`), with the same entries as
        its Feeds. Feeds don't need to be enabled. The response sets `Content-Disposition` to
        `attachment; filename=Helium_<email-local-part>_<calendar>_<YYYY-MM-DD>.ics`, so a browser will save it as a
        dated download.

        To keep another calendar app in sync instead, subscribe to the Feeds (`PUT /feed/private/enable/`).
        """
        user = self.request.user
        calendar = request.query_params.get('calendar', 'all')
        if calendar not in _ICS_EXPORTS:
            raise ValidationError({'calendar': gettext('Must be one of: %(calendars)s.') % {
                'calendars': ', '.join(_ICS_EXPORTS)}},
                                  code=errorcodes.INVALID_CHOICE)

        return _download_response(user, _ICS_EXPORTS[calendar](user), 'text/calendar; charset=utf-8', 'ics',
                                  label=calendar)


def _download_response(user, content, content_type, extension, label=None):
    email_local = user.email.split('@')[0] if user.email else 'backup'
    name = '_'.join(part for part in ('Helium', email_local, label, timezone.now().strftime('%Y-%m-%d')) if part)
    filename = f'{name}.{extension}'

    response = HttpResponse(content, content_type=content_type)
    response['Filename'] = filename
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response
