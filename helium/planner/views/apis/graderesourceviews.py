import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.views.base import HeliumAPIView
from helium.planner.serializers.gradeserializer import GradeSerializer, NeededGradeSerializer
from helium.planner.services import gradingservice, neededgradeservice

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


@extend_schema(
    tags=['planner.grades']
)
class NeededGradeApiResourceView(HeliumAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = NeededGradeSerializer

    @extend_schema(
        summary="Calculate the grade the User needs in a Course",
        parameters=[
            OpenApiParameter(name='course', type=int, required=True, description='The Course ID.'),
            OpenApiParameter(
                name='target', type=int, required=True,
                description='For a class with weighted grading, the ID of a category that is down to its last '
                            'ungraded assignment. Otherwise, the ID of an ungraded assignment in the class.'),
            OpenApiParameter(name='desired_grade', type=float, required=True,
                             description='The overall class grade to reach, from 0 to 100.'),
        ],
    )
    def get(self, request, *args, **kwargs):
        """
        Return the score needed to bring a class's overall grade to `desired_grade`. This is the "What Do I Need?"
        grade calculator in the app, worked out from the same grades `GET /planner/grades/` returns.

        For a class with weighted grading, the result is the score needed on the category's last ungraded assignment
        (or the category average, when that assignment isn't in the class's ungraded work). Categories with nothing
        graded yet count as `0`. For a class graded by points, it's the score needed on the chosen assignment.
        """
        try:
            course_id = int(request.query_params['course'])
            target_id = int(request.query_params['target'])
            desired_grade = float(request.query_params['desired_grade'])
        except (KeyError, ValueError):
            raise ValidationError("'course', 'target', and 'desired_grade' must be given as numbers")

        needed = neededgradeservice.get_needed_grade(request.user.pk, course_id, target_id, desired_grade)

        return Response(NeededGradeSerializer(needed).data)
