import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.views import HeliumAPIView
from helium.planner.serializers.gradeserializer import GradeSerializer
from helium.planner.services import gradingservice

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class GradesApiResourceView(HeliumAPIView):
    """
    get:
    Return the grades for the authenticated user.

    The result is a list of course groups. Each course group contains a nested list of courses. Each course contains a
    nested list of categories.

    Each entity contains three fields: `id`, `overall_grade`, and `grade_points`.

    `grade_points` represents a list of grades accumulating over time. This is a list made up of individual grade
    points, each a tuple containing two values of the format [time, grade_at_time].
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        grade_data = gradingservice.get_grade_data(request.user.pk)

        serializer = GradeSerializer(grade_data)

        return Response(serializer.data)
