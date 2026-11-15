import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Course
from helium.planner.tests.helpers import coursegrouphelper, coursehelper


class TestCaseCourseGradeScaleViews(APITestCase):
    def _course_data(self, **fields):
        return {
            'title': 'Biology',
            'credits': '3.00',
            'color': '#4986e7',
            'start_date': '2017-01-06',
            'end_date': '2017-05-08',
            **fields,
        }

    def _create_course(self, course_group, **fields):
        return self.client.post(reverse('planner_coursegroups_courses_list',
                                        kwargs={'course_group': course_group.pk}),
                                json.dumps(self._course_data(**fields)), content_type='application/json')

    def _patch_course(self, course, **fields):
        return self.client.patch(reverse('planner_coursegroups_courses_detail',
                                         kwargs={'course_group': course.course_group_id, 'pk': course.pk}),
                                 json.dumps(fields), content_type='application/json')

    def test_create_with_a_compatible_preset(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(
            user, grade_scale_template=enums.GRADE_SCALE_4_0_PLUS_MINUS)

        # WHEN
        response = self._create_course(course_group, grade_scale_template=enums.GRADE_SCALE_4_0)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['grade_scale_template'], enums.GRADE_SCALE_4_0)
        self.assertEqual(Course.objects.get(pk=response.data['id']).grade_scale_template, enums.GRADE_SCALE_4_0)

    def test_create_without_a_preset_uses_the_group_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        response = self._create_course(course_group)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['grade_scale_template'])

    def test_create_with_a_preset_that_does_not_fit_the_group_is_rejected(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale_template=enums.GRADE_SCALE_4_0)

        # WHEN
        response = self._create_course(course_group, grade_scale_template=enums.GRADE_SCALE_4_0_PLUS_MINUS)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade_scale_template', response.data)
        self.assertIn('Compatible presets: 4.0.', str(response.data['grade_scale_template']))
        self.assertFalse(Course.objects.exists())

    def test_create_with_a_preset_when_the_group_has_no_scale_is_rejected(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale_template=enums.GRADE_SCALE_NONE)

        # WHEN
        response = self._create_course(course_group, grade_scale_template=enums.GRADE_SCALE_4_0)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The group has no grade scale.', str(response.data['grade_scale_template']))

    def test_create_with_the_none_preset_is_rejected(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        response = self._create_course(course_group, grade_scale_template=enums.GRADE_SCALE_NONE)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade_scale_template', response.data)

    def test_update_sets_and_clears_the_preset(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(
            user, grade_scale_template=enums.GRADE_SCALE_4_0_PLUS_MINUS)
        course = coursehelper.given_graded_course_exists(course_group, 91, credits=3)

        # WHEN
        set_response = self._patch_course(course, grade_scale_template=enums.GRADE_SCALE_4_0)
        set_grade_point = Course.objects.get(pk=course.pk).grade_point
        clear_response = self._patch_course(course, grade_scale_template=None)

        # THEN
        self.assertEqual(set_response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(set_grade_point), 4.0)
        self.assertEqual(clear_response.status_code, status.HTTP_200_OK)
        course.refresh_from_db()
        self.assertIsNone(course.grade_scale_template)
        self.assertEqual(float(course.grade_point), 3.7)

    def test_update_with_a_preset_that_does_not_fit_the_group_is_rejected(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale_template=enums.GRADE_SCALE_4_0)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self._patch_course(course, grade_scale_template=enums.GRADE_SCALE_10_0)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        course.refresh_from_db()
        self.assertIsNone(course.grade_scale_template)

    def test_update_without_the_preset_keeps_it(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(
            user, grade_scale_template=enums.GRADE_SCALE_4_0_PLUS_MINUS)
        course = coursehelper.given_course_exists(course_group, grade_scale_template=enums.GRADE_SCALE_4_0)

        # WHEN
        response = self._patch_course(course, title='Renamed')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course.refresh_from_db()
        self.assertEqual(course.grade_scale_template, enums.GRADE_SCALE_4_0)
