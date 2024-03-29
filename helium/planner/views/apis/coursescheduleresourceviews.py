__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.views import HeliumAPIView
from helium.planner.models import Course, CourseSchedule
from helium.planner.schemas import CourseScheduleDetailSchema
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)


class CourseScheduleAsEventsResourceView(HeliumAPIView):
    """
    get:
    Return all course schedules as a list of event instances.
    """
    permission_classes = (IsAuthenticated,)
    schema = CourseScheduleDetailSchema()

    def get(self, request, *args, **kwargs):
        user = self.request.user
        try:
            course = Course.objects.get(pk=self.kwargs['course'])
            course_schedules = CourseSchedule.objects.for_user(user.pk).for_course(course.pk)

            events = coursescheduleservice.course_schedules_to_events(course, course_schedules)

            serializer = EventSerializer(events, many=True)

            return Response(serializer.data)
        except Course.DoesNotExist:
            raise NotFound('Course not found.')
        except CourseSchedule.DoesNotExist:
            raise NotFound('CourseSchedule not found.')
