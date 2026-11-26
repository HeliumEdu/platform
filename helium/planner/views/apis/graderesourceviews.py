import logging

from django.utils.translation import gettext
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common import errorcodes
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
        `cumulative_grade`, `impact_score`, and `gpa`. Items with `graded: true` represent completed graded homework;
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
                description='For a course with weighted grading, the ID of a category that is down to its last '
                            'ungraded homework. Otherwise, the ID of an ungraded homework in the course.'),
            OpenApiParameter(name='desired_grade', type=float, required=False,
                             description='The overall course grade to reach, from 0 to 100. Give this or '
                                         '`desired_gpa`.'),
            OpenApiParameter(name='desired_gpa', type=float, required=False,
                             description='The course group GPA to reach, on the course\'s `grade_scale`. Give this or '
                                         '`desired_grade`. Needs the course to have credits and a grade scale.'),
        ],
    )
    def get(self, request, *args, **kwargs):
        """
        Return the score needed to bring a course's overall grade to `desired_grade`, or its course group's GPA to
        `desired_gpa`.
        It's worked out from the same grades `GET /planner/grades/` returns. With `desired_gpa`, the GPA is rounded to
        two places.

        For a course with weighted grading, the result is the score needed on the category's last ungraded homework
        (or the category average, when that homework isn't in the course's ungraded work). For a course graded by
        points, it's the score needed on the chosen homework. Either way, the course's other ungraded work is assumed
        to score as the course does now: in a course with weighted grading, each other category at its average, or at
        the course's grade while nothing in it is graded; otherwise, at the course's grade.
        """
        try:
            course_id = int(request.query_params['course'])
            target_id = int(request.query_params['target'])
            desired_grade = _optional_float(request.query_params.get('desired_grade'))
            desired_gpa = _optional_float(request.query_params.get('desired_gpa'))
        except (KeyError, ValueError):
            raise ValidationError(gettext("'course', 'target', 'desired_grade', and 'desired_gpa' must be given as "
                                          'numbers'),
                                  code=errorcodes.NEEDED_GRADE_PARAMS_INVALID)

        needed = neededgradeservice.get_needed_grade(request.user.pk, course_id, target_id,
                                                     desired_grade=desired_grade, desired_gpa=desired_gpa)

        return Response(NeededGradeSerializer(needed).data)


def _optional_float(value):
    return None if value is None else float(value)
