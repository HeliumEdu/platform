import logging

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.planner.models import CourseSchedule
from helium.planner.schemas import CourseScheduleDetailSchema
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.services import coursescheduleservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


class CourseScheduleAsEventsResourceView(GenericAPIView):
    """
    get:
    Return a course's schedule as a list of event instances.
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = CourseScheduleDetailSchema()

    def get_queryset(self):
        user = self.request.user
        return CourseSchedule.objects.for_user(user.pk).for_course(self.kwargs['course'])

    def get(self, request, *args, **kwargs):
        course_schedule = self.get_object()

        events = coursescheduleservice.course_schedule_to_events(course_schedule)

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)
