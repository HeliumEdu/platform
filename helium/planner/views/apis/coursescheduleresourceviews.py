__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.7"

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.base import HeliumAPIView
from helium.planner.models import Course, CourseSchedule
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.courseschedule.event']
)
class CourseScheduleAsEventsResourceView(HeliumAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return all schedules for the given course as a list of event instances.
        """
        user = self.request.user
        try:
            course = Course.objects.for_user(user.pk).get(pk=self.kwargs['course'])
            course_schedules = CourseSchedule.objects.for_user(user.pk).for_course(course.pk)
            search = request.query_params["search"].lower() if "search" in request.query_params else None

            events = coursescheduleservice.course_schedules_to_events(course, course_schedules, search)

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
