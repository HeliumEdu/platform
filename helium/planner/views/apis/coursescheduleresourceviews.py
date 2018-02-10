import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.planner.models import Course, CourseSchedule
from helium.planner.schemas import CourseScheduleDetailSchema
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.services import coursescheduleservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


class CourseScheduleAsEventsResourceView(APIView):
    """
    get:
    Return all course schedules as a list of event instances.
    """
    permission_classes = (IsAuthenticated,)
    schema = CourseScheduleDetailSchema()

    def get(self, request, *args, **kwargs):
        user = self.request.user
        course = Course.objects.get(pk=self.kwargs['course'])
        course_schedules = CourseSchedule.objects.for_user(user.pk).for_course(course.pk)

        events = coursescheduleservice.course_schedules_to_events(course, course_schedules)

        serializer = EventSerializer(events, many=True)

        return Response(serializer.data)
