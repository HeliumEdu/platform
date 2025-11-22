__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.22"

import logging
from datetime import datetime

from dateutil import parser
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.planner.models import Course, CourseSchedule, Attachment
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.services import coursescheduleservice
from helium.planner.views.base import HeliumCalendarItemAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.courseschedule.event', 'calendar.user']
)
class UserCourseScheduleAsEventsListView(HeliumCalendarItemAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return all schedules that should be shown on the calendar for the authenticated user as a list of CourseSchedule Event instances.
        """
        return super().get(request, *args, **kwargs)

    def list(self, request, *arg, **kwargs):
        user = self.request.user
        courses = (Course.objects
                   .for_user(user.pk))
        if 'shown_on_calendar' in request.query_params:
            courses = courses.filter(course_group__shown_on_calendar=request.query_params['shown_on_calendar'].lower() == 'true')
        course_schedules = (CourseSchedule.objects
                            .filter(course__in=courses))

        _from = parser.parse(request.query_params["from"]).astimezone(timezone.utc) \
            if "from" in request.query_params else None
        to = parser.parse(request.query_params["to"]).astimezone(timezone.utc) \
            if "to" in request.query_params else None
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        events = []
        for course in courses:
            events += coursescheduleservice.course_schedules_to_events(course,
                                                                       course_schedules.filter(course=course.id),
                                                                       _from, to, search)

        serializer = EventSerializer(events, many=True)

        attachments = list(Attachment.objects.filter(course__in=courses))
        if len(attachments) > 0:
            attachments_serializer = AttachmentSerializer(attachments, many=True)
            for event in serializer.data:
                event['attachments'] = attachments_serializer.data

        return Response(serializer.data)


@extend_schema(
    tags=['planner.courseschedule.event']
)
class CourseScheduleAsEventsListView(HeliumCalendarItemAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return all schedules for the given course as a list of CourseSchedule Event instances.
        """
        return super().get(request, *args, **kwargs)

    def list(self, request, *arg, **kwargs):
        user = self.request.user
        try:
            course = Course.objects.for_user(user.pk).get(pk=self.kwargs['course'])
            course_schedules = CourseSchedule.objects.for_user(user.pk).for_course(course.pk)

            _from = parser.parse(request.query_params["from"]).astimezone(timezone.utc) \
                if "from" in request.query_params else None
            to = parser.parse(request.query_params["to"]).astimezone(timezone.utc) \
                if "to" in request.query_params else None
            search = request.query_params["search"].lower() if "search" in request.query_params else None

            events = coursescheduleservice.course_schedules_to_events(course, course_schedules, _from, to, search)

            serializer = EventSerializer(events, many=True)

            attachments = list(course.attachments.all())
            if len(attachments) > 0:
                attachments_serializer = AttachmentSerializer(attachments, many=True)
                for event in serializer.data:
                    event['attachments'] = attachments_serializer.data

            return Response(serializer.data)
        except Course.DoesNotExist:
            raise NotFound('No Course matches the given query.')
        except CourseSchedule.DoesNotExist:
            raise NotFound('No CourseSchedule matches the given query.')
