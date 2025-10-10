__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.views import HeliumAPIView
from helium.planner.models import Course, CourseSchedule
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)


# class UserCourseScheduleAsEventsResourceView(HeliumAPIView, ListModelMixin):
#     serializer_class = EventSerializer
#     permission_classes = (IsAuthenticated,)
#     filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
#     filterset_class = HomeworkFilter
#     search_fields = ('title', 'comments', 'category__title', 'course__title',)
#     order_fields = ('title', 'start', 'completed', 'priority', 'category__title', 'course__title',)
#
#     def get_queryset(self):
#         if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
#             user = self.request.user
#             return Course.objects.for_user(user.pk)
#         else:
#             return Course.objects.none()
#
#     def get(self, request, *args, **kwargs):
#         """
#         Return a list of all homework instances for the authenticated user. For convenience, homework instances on a
#         GET are serialized with representations of associated attachments and reminders to avoid the need for redundant
#         API calls.
#         """
#         for course in
#         response = self.list(request, *args, **kwargs)
#
#         return response


class CourseScheduleAsEventsResourceView(HeliumAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        Return all schedules for the given course as a list of event instances.
        """
        user = self.request.user
        try:
            course = Course.objects.get(pk=self.kwargs['course'])
            course_schedules = CourseSchedule.objects.for_user(user.pk).for_course(course.pk)
            search = request.query_params["search"].lower() if "search" in request.query_params else None

            events = coursescheduleservice.course_schedules_to_events(course, course_schedules, search)

            serializer = EventSerializer(events, many=True)

            return Response(serializer.data)
        except Course.DoesNotExist:
            raise NotFound('No Course matches the given query.')
        except CourseSchedule.DoesNotExist:
            raise NotFound('No CourseSchedule matches the given query.')
