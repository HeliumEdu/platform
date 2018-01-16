import logging

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.planner.serializers.gradeserializer import GradeSerializer
from helium.planner.services import gradingservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class GradesApiListView(GenericAPIView):
    """
    get:
    Return the grades for the authenticated user.

    The result is a list of course groups. Each course group contains a nested list of courses. Each course contains a
    nested list of categories.

    Each entity contains three fields: `id`, `overall_grade`, and `grade_points`.

    `grade_points` is only populated for courses, and it represents a list of grades accumulating over time. This is a
    list made up of individual grade points, each a tuple containing two values of the format [time, grade_at_time].
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = GradeSerializer

    def get(self, request, *args, **kwargs):
        grade_data = gradingservice.get_grade_data(request.user.pk)

        serializer = self.get_serializer(grade_data)

        return Response(serializer.data)
