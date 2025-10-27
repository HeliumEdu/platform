__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.6"

import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.views import HeliumAPIView
from helium.planner.serializers.gradeserializer import GradeSerializer
from helium.planner.services import gradingservice

logger = logging.getLogger(__name__)


class GradesApiResourceView(HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = GradeSerializer

    def get(self, request, *args, **kwargs):
        """
        Return the grades for the authenticated user.

        The result is a list of course groups. Each course group contains a nested list of courses. Each course
        contains a nested list of categories.

        Each entity contains at least three fields: `id`, `overall_grade`, and `grade_points`.

        `grade_points` represents a list of grades accumulating over time. This is a list made up of individual grade
        points, each a tuple containing values of the format [time, grade_at_time, homework_id, homework_title,
        homework_grade, category_id].
        """
        grade_data = gradingservice.get_grade_data(request.user.pk)

        serializer = GradeSerializer(grade_data)

        return Response(serializer.data)
