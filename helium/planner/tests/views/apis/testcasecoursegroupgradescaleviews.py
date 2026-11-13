import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.utils import gradeutils
from helium.planner.models import Course, CourseGroup
from helium.planner.tests.helpers import coursegrouphelper, coursehelper

_CUSTOM_SCALE = [
    {'min_grade': 0, 'grade_point': 0, 'label': 'Fail'},
    {'min_grade': 50, 'grade_point': 2, 'label': 'Pass'},
    {'min_grade': 80, 'grade_point': 4, 'label': 'Merit'},
]


class TestCaseCourseGroupGradeScaleViews(APITestCase):
    def _create_course_group(self, **fields):
        data = {
            'title': 'Spring',
            'start_date': '2018-01-08',
            'end_date': '2018-05-04',
            'shown_on_calendar': True,
            **fields,
        }
        return self.client.post(reverse('planner_coursegroups_list'), json.dumps(data),
                                content_type='application/json')

    def _put_course_group(self, course_group, **fields):
        data = {
            'title': course_group.title,
            'start_date': course_group.start_date.isoformat(),
            'end_date': course_group.end_date.isoformat(),
            'shown_on_calendar': course_group.shown_on_calendar,
            **fields,
        }
        return self.client.put(reverse('planner_coursegroups_detail', kwargs={'pk': course_group.pk}),
                               json.dumps(data), content_type='application/json')

    def test_create_with_each_template_fills_its_scale(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        for template, preset in enums.GRADE_SCALE_TEMPLATES.items():
            with self.subTest(template=template):
                # WHEN
                response = self._create_course_group(grade_scale_template=template)

                # THEN
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data['grade_scale_template'], template)
                self.assertEqual(response.data['grade_scale'], preset['scale'])
                self.assertEqual(CourseGroup.objects.get(pk=response.data['id']).grade_scale, preset['scale'])

    def test_create_with_a_preset_scale_derives_its_template(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        for template, preset in enums.GRADE_SCALE_TEMPLATES.items():
            with self.subTest(template=template):
                # WHEN
                response = self._create_course_group(grade_scale=preset['scale'])

                # THEN
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data['grade_scale_template'], template)

    def test_create_with_a_custom_scale_has_no_template(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(grade_scale=_CUSTOM_SCALE)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['grade_scale_template'])
        self.assertEqual([band['grade_point'] for band in response.data['grade_scale']], [0.0, 2.0, 4.0])

    def test_template_with_a_custom_scale_is_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(grade_scale_template=enums.GRADE_SCALE_4_5, grade_scale=_CUSTOM_SCALE)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade_scale_template', response.data)
        self.assertFalse(CourseGroup.objects.exists())

    def test_template_with_another_presets_scale_is_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(grade_scale_template=enums.GRADE_SCALE_4_5,
                                             grade_scale=gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_0))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade_scale_template', response.data)

    def test_template_with_its_own_scale_is_accepted(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(grade_scale_template=enums.GRADE_SCALE_4_5,
                                             grade_scale=gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_5))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_4_5)

    def test_put_with_template_and_a_conflicting_scale_is_rejected(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        response = self._put_course_group(course_group, grade_scale_template=enums.GRADE_SCALE_4_5,
                                          grade_scale=_CUSTOM_SCALE)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        course_group.refresh_from_db()
        self.assertEqual(course_group.grade_scale_template, enums.GRADE_SCALE_4_0)

    def test_create_copies_the_most_recent_groups_scale_skipping_the_example(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        coursegrouphelper.given_course_group_exists(user, start_date=datetime.date(2016, 1, 6),
                                                    grade_scale=_CUSTOM_SCALE)
        coursegrouphelper.given_course_group_exists(user, start_date=datetime.date(2017, 1, 6), example_schedule=True,
                                                    grade_scale_template=enums.GRADE_SCALE_4_5)

        # WHEN
        response = self._create_course_group()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['grade_scale_template'])
        self.assertEqual(CourseGroup.objects.get(pk=response.data['id']).grade_scale, _CUSTOM_SCALE)

    def test_create_copies_a_most_recent_group_without_a_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        coursegrouphelper.given_course_group_exists(user, start_date=datetime.date(2016, 1, 6),
                                                    grade_scale_template=enums.GRADE_SCALE_4_5)
        coursegrouphelper.given_course_group_exists(user, start_date=datetime.date(2017, 1, 6),
                                                    grade_scale_template=enums.GRADE_SCALE_NONE)

        # WHEN
        response = self._create_course_group()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_NONE)
        self.assertEqual(response.data['grade_scale'], [])

    def test_first_group_has_no_scale(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_NONE)
        self.assertEqual(response.data['grade_scale'], [])
        self.assertEqual(float(response.data['gpa']), -1)

    def test_first_group_after_the_example_has_no_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        coursegrouphelper.given_course_group_exists(user, example_schedule=True,
                                                    grade_scale_template=enums.GRADE_SCALE_4_0)

        # WHEN
        response = self._create_course_group()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_NONE)

    def test_put_without_scale_keeps_it(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale=_CUSTOM_SCALE)

        # WHEN
        response = self._put_course_group(course_group, title='Renamed')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_group.refresh_from_db()
        self.assertEqual(course_group.title, 'Renamed')
        self.assertEqual(course_group.grade_scale, _CUSTOM_SCALE)
        self.assertIsNone(course_group.grade_scale_template)

    def test_put_with_null_template_and_no_scale_keeps_a_preset_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale_template=enums.GRADE_SCALE_7_0)

        # WHEN
        response = self._put_course_group(course_group, grade_scale_template=None)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_7_0)

    def test_changing_the_scale_recalculates_grade_points_and_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_graded_course_exists(course_group, 96, credits=3)

        # WHEN
        response = self._put_course_group(course_group, grade_scale_template=enums.GRADE_SCALE_4_5)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['gpa']), 4.5)
        self.assertEqual(float(Course.objects.get(pk=course.pk).grade_point), 4.5)

    def test_switching_to_no_scale_clears_grade_points_and_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_graded_course_exists(course_group, 96, credits=3)

        # WHEN
        response = self._put_course_group(course_group, grade_scale_template=enums.GRADE_SCALE_NONE)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['grade_scale'], [])
        self.assertEqual(float(response.data['gpa']), -1)
        self.assertEqual(float(Course.objects.get(pk=course.pk).grade_point), -1)

    def test_an_empty_scale_is_no_scale(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(grade_scale=[])

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_NONE)

    def test_invalid_scales_are_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        invalid_scales = {
            'not a list': 'A',
            'too few bands': [{'min_grade': 0, 'grade_point': 0}],
            'too many bands': [{'min_grade': i, 'grade_point': i} for i in range(21)],
            'first band above 0': [{'min_grade': 10, 'grade_point': 0}, {'min_grade': 50, 'grade_point': 1}],
            'min_grade not ascending': [{'min_grade': 0, 'grade_point': 0}, {'min_grade': 50, 'grade_point': 1},
                                        {'min_grade': 50, 'grade_point': 2}],
            'min_grade above 100': [{'min_grade': 0, 'grade_point': 0}, {'min_grade': 101, 'grade_point': 1}],
            'grade_point negative': [{'min_grade': 0, 'grade_point': -1}, {'min_grade': 50, 'grade_point': 1}],
            'grade_point not monotone': [{'min_grade': 0, 'grade_point': 0}, {'min_grade': 50, 'grade_point': 2},
                                         {'min_grade': 80, 'grade_point': 1}],
            'too many decimal places': [{'min_grade': 0, 'grade_point': 0}, {'min_grade': 50, 'grade_point': 1.333}],
            'label too long': [{'min_grade': 0, 'grade_point': 0}, {'min_grade': 50, 'grade_point': 1,
                                                                    'label': 'Exceptional!'}],
            'missing grade_point': [{'min_grade': 0, 'grade_point': 0}, {'min_grade': 50}],
        }

        for case, grade_scale in invalid_scales.items():
            with self.subTest(case=case):
                # WHEN
                response = self._create_course_group(grade_scale=grade_scale)

                # THEN
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, case)
                self.assertIn('grade_scale', response.data, case)

        self.assertEqual(CourseGroup.objects.count(), 0)

    def test_scale_where_lower_is_better_is_valid(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(
            grade_scale=gradeutils.preset_grade_scale(enums.GRADE_SCALE_1_5_PASS_50))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_1_5_PASS_50)

    def test_unknown_template_is_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(grade_scale_template=99)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade_scale_template', response.data)

    def test_gpa_is_read_only(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._create_course_group(gpa=3.9)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['gpa']), -1)
