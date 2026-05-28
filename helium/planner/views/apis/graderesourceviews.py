__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.base import HeliumAPIView
from helium.planner.serializers.gradeserializer import GradeSerializer
from helium.planner.services import gradingservice

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.grades']
)
class GradesApiResourceView(HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = GradeSerializer

    @extend_schema(summary="Retrieve the User's grade summary")
    def get(self, request, *args, **kwargs):
        """
        Return the grades for the authenticated user.

        The result is a list of course groups. Each course group contains a nested list of courses. Each course
        contains a nested list of categories.

        Each entity contains at least three fields: `id`, `overall_grade`, and `homework_series`. An `overall_grade`
        of `-1` is the sentinel for "no graded homework yet" — not a real percentage.

        `homework_series` is a chronologically sorted list of homework items. Each item is a dict with fields:
        `id`, `title`, `start`, `category_id`, `course_id`, `points_possible`, `graded`, `homework_grade`,
        `cumulative_grade`, and `impact_score`. Items with `graded: true` represent completed graded homework;
        items with `graded: false` represent pending homework with a projected `impact_score`.
        """
        grade_data = gradingservice.get_grade_data(request.user.pk)

        serializer = GradeSerializer(grade_data)

        return Response(serializer.data)
