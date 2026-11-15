import datetime

from dateutil import parser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.tests.helpers import commonhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper


def _graded_series(holder):
    return [item for item in holder['homework_series'] if item['graded']]


class TestCaseGradeResourceViews(APITestCase):
    def _given_class_to_plan_for_gpa(self, user, grade_scale_template=enums.GRADE_SCALE_4_0_PLUS_MINUS,
                                     other_grade=85, other_credits=3, credits=3, class_grade_scale_template=None):
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale_template=grade_scale_template)
        coursehelper.given_graded_course_exists(course_group, other_grade, credits=other_credits)
        course = coursehelper.given_course_exists(course_group, title='Biology', credits=credits,
                                                  grade_scale_template=class_grade_scale_template)
        category = categoryhelper.given_category_exists(course, weight=0)
        homeworkhelper.given_homework_exists(course, category=category, completed=True, current_grade='45/50')
        project = homeworkhelper.given_homework_exists(course, title='Project', category=category,
                                                       current_grade='-1/100')
        return course, project

    def _get_needed(self, course, target, **desired):
        return self.client.get(reverse('planner_resource_grades_needed'),
                               {'course': course.pk, 'target': target.pk, **desired})

    def test_grade_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_resource_grades'))
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

    def test_get_grades(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group1 = coursegrouphelper.given_course_group_exists(user)
        course_group2 = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        category1 = categoryhelper.given_category_exists(course1, weight=50)
        category2 = categoryhelper.given_category_exists(course1, title='Test Category 2', weight=50)
        # This category having no weight will result in the course not having weighted grading
        category3 = categoryhelper.given_category_exists(course2, title='Test Category 3', weight=0)
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='20/30')
        homework2 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='25/30')
        homework3 = homeworkhelper.given_homework_exists(course1, category=category2, completed=True,
                                                         current_grade='15/30')
        homework4 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='20/30')
        homework5 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='25/30')
        # Incomplete homework are not graded
        homeworkhelper.given_homework_exists(course1, category=category2, current_grade='-1/100')
        # Completed homework with no grade set are not graded
        homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                             current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('planner_resource_grades'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['course_groups']), 2)
        self.assertEqual(len(response.data['course_groups'][0]['courses']), 1)
        self.assertEqual(len(response.data['course_groups'][1]['courses']), 1)
        self.assertEqual(len(response.data['course_groups'][0]['courses'][0]['categories']), 2)
        self.assertEqual(len(response.data['course_groups'][1]['courses'][0]['categories']), 1)
        self.assertEqual(len(_graded_series(response.data['course_groups'][0]['courses'][0])), 3)
        self.assertEqual(len(_graded_series(response.data['course_groups'][1]['courses'][0])), 2)

        self.assertIn('title', response.data['course_groups'][0])
        self.assertEqual(float(response.data['course_groups'][0]['overall_grade']), 62.5)
        self.assertIn('trend', response.data['course_groups'][0])
        self.assertIn('num_homework_graded', response.data['course_groups'][0])

        self.assertIn('title', response.data['course_groups'][0]['courses'][0])
        self.assertIn('color', response.data['course_groups'][0]['courses'][0])
        self.assertEqual(float(response.data['course_groups'][0]['courses'][0]['overall_grade']), 62.5)
        self.assertIn('trend', response.data['course_groups'][0]['courses'][0])
        self.assertIn('num_homework_graded', response.data['course_groups'][0]['courses'][0])
        self.assertIn('has_weighted_grading', response.data['course_groups'][0]['courses'][0])
        self.assertEqual(response.data['course_groups'][0]['courses'][0]['points_earned'], 60)
        self.assertEqual(response.data['course_groups'][0]['courses'][0]['points_possible'], 90)

        graded = _graded_series(response.data['course_groups'][0]['courses'][0])
        self.assertEqual(parser.parse(graded[0]['start']), homework1.start)
        self.assertEqual(graded[0]['cumulative_grade'], 66.6667)
        self.assertEqual(parser.parse(graded[1]['start']), homework2.start)
        self.assertEqual(graded[1]['cumulative_grade'], 75.0)
        self.assertEqual(parser.parse(graded[2]['start']), homework3.start)
        self.assertEqual(graded[2]['cumulative_grade'], 62.5)

        self.assertIn('title', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertEqual(float(response.data['course_groups'][0]['courses'][0]['categories'][1]['overall_grade']),
                          75.0)
        self.assertIn('trend', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('num_homework_graded', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('weight', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('color', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('grade_by_weight', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertEqual(response.data['course_groups'][0]['courses'][0]['categories'][0]['points_earned'], 15)
        self.assertEqual(response.data['course_groups'][0]['courses'][0]['categories'][0]['points_possible'], 30)

        self.assertIn('title', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertEqual(float(response.data['course_groups'][0]['courses'][0]['categories'][0]['overall_grade']),
                          50.0)
        self.assertIn('trend', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('num_homework_graded', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('weight', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('color', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('grade_by_weight', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertEqual(response.data['course_groups'][0]['courses'][0]['categories'][1]['points_earned'], 45)
        self.assertEqual(response.data['course_groups'][0]['courses'][0]['categories'][1]['points_possible'], 60)

        self.assertIn('title', response.data['course_groups'][1])
        self.assertEqual(float(response.data['course_groups'][1]['overall_grade']), 75.0)
        self.assertIn('trend', response.data['course_groups'][1])
        self.assertIn('num_homework_graded', response.data['course_groups'][1])

        self.assertIn('title', response.data['course_groups'][1]['courses'][0])
        self.assertEqual(float(response.data['course_groups'][1]['courses'][0]['overall_grade']), 75.0)
        self.assertIn('trend', response.data['course_groups'][1]['courses'][0])
        self.assertIn('num_homework_graded', response.data['course_groups'][1]['courses'][0])
        self.assertIn('has_weighted_grading', response.data['course_groups'][1]['courses'][0])
        self.assertEqual(response.data['course_groups'][1]['courses'][0]['points_earned'], 45)
        self.assertEqual(response.data['course_groups'][1]['courses'][0]['points_possible'], 60)

        graded = _graded_series(response.data['course_groups'][1]['courses'][0])
        self.assertEqual(parser.parse(graded[0]['start']), homework4.start)
        self.assertEqual(graded[0]['cumulative_grade'], 66.6667)
        self.assertEqual(parser.parse(graded[1]['start']), homework5.start)
        self.assertEqual(graded[1]['cumulative_grade'], 75.0)

        self.assertIn('title', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertEqual(float(response.data['course_groups'][1]['courses'][0]['categories'][0]['overall_grade']),
                          75.0)
        self.assertIn('trend', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('num_homework_graded', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('weight', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('color', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('grade_by_weight', response.data['course_groups'][1]['courses'][0]['categories'][0])

    def test_needed_grade_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self.client.get(reverse('planner_resource_grades_needed'),
                                    {'course': 1, 'target': 1, 'desired_grade': 85})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_needed_grade_weighted_solves_for_the_categorys_remaining_assignment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        homework = categoryhelper.given_category_exists(course, title='Homework', weight=60)
        exams = categoryhelper.given_category_exists(course, title='Exams', weight=40)
        homeworkhelper.given_homework_exists(course, category=homework, completed=True, current_grade='45/50')
        homeworkhelper.given_homework_exists(course, category=exams, completed=True, current_grade='40/50')
        final = homeworkhelper.given_homework_exists(course, title='Final', category=exams, current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('planner_resource_grades_needed'),
                                   {'course': course.pk, 'target': exams.pk, 'desired_grade': 85})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual('achievable', response.data['state'])
        self.assertTrue(response.data['weighted'])
        self.assertEqual({'id': exams.pk, 'title': 'Exams'}, response.data['category'])
        self.assertAlmostEqual(76.25, response.data['needed_grade'], places=4,
                               msg='Exams needs (8500 - 60 × 90) / 40 = 77.5%; on the final, (0.775 × 150 - 40) / 100')
        self.assertEqual(final.pk, response.data['assignment']['id'])
        self.assertAlmostEqual(76.25, response.data['assignment']['needed_points'], places=4)
        self.assertEqual(100, response.data['assignment']['points_possible'])
        self.assertIsNone(response.data['total_weight_accounted_for'])

    def test_needed_grade_weighted_solves_for_the_last_remaining_occurrence_of_a_repeating_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        homework = categoryhelper.given_category_exists(course, title='Homework', weight=60)
        exams = categoryhelper.given_category_exists(course, title='Exams', weight=40)
        homeworkhelper.given_homework_exists(course, category=homework, completed=True, current_grade='45/50')
        homeworkhelper.given_homework_exists(course, category=exams, completed=True, current_grade='40/50')
        series = homeworkhelper.given_homework_exists(course, title='Unit exam', category=exams,
                                                      recurrence_rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2',
                                                      exception_dates=['2017-05-08T16:00:00Z'])

        # WHEN
        response = self.client.get(reverse('planner_resource_grades_needed'),
                                   {'course': course.pk, 'target': exams.pk, 'desired_grade': 85})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual('achievable', response.data['state'])
        self.assertEqual(series.pk, response.data['assignment']['id'])
        self.assertAlmostEqual(76.25, response.data['assignment']['needed_points'], places=4)
        self.assertEqual(100, response.data['assignment']['points_possible'])

    def test_needed_grade_points_based_solves_for_the_chosen_assignment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        category = categoryhelper.given_category_exists(course, weight=0)
        homeworkhelper.given_homework_exists(course, category=category, completed=True, current_grade='30/50')
        homeworkhelper.given_homework_exists(course, category=category, completed=True, current_grade='30/60')
        project = homeworkhelper.given_homework_exists(course, title='Project', category=category,
                                                       current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('planner_resource_grades_needed'),
                                   {'course': course.pk, 'target': project.pk, 'desired_grade': 70})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual('achievable', response.data['state'])
        self.assertFalse(response.data['weighted'])
        self.assertIsNone(response.data['category'])
        self.assertAlmostEqual(87, response.data['needed_grade'], places=4, msg='(0.7 × 210 − 60) / 100 = 87%')
        self.assertAlmostEqual(87, response.data['assignment']['needed_points'], places=4)

    def test_needed_grade_reports_weights_that_dont_total_100(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        homework = categoryhelper.given_category_exists(course, title='Homework', weight=40)
        exams = categoryhelper.given_category_exists(course, title='Exams', weight=40)
        homeworkhelper.given_homework_exists(course, category=homework, completed=True, current_grade='45/50')
        homeworkhelper.given_homework_exists(course, category=exams, current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('planner_resource_grades_needed'),
                                   {'course': course.pk, 'target': exams.pk, 'desired_grade': 85})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual('invalid_total_weight', response.data['state'])
        self.assertAlmostEqual(80, response.data['total_weight_accounted_for'])
        self.assertIsNone(response.data['assignment'])

    def test_needed_grade_refuses_ineligible_targets(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        weighted = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        exams = categoryhelper.given_category_exists(weighted, title='Exams', weight=100)
        homeworkhelper.given_homework_exists(weighted, category=exams, current_grade='-1/100')
        homeworkhelper.given_homework_exists(weighted, category=exams, current_grade='-1/100')
        points_based = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        category = categoryhelper.given_category_exists(points_based, weight=0)
        graded = homeworkhelper.given_homework_exists(points_based, category=category, completed=True,
                                                      current_grade='30/50')

        # WHEN
        responses = [
            self.client.get(reverse('planner_resource_grades_needed'),
                            {'course': weighted.pk, 'target': exams.pk, 'desired_grade': 85}),
            self.client.get(reverse('planner_resource_grades_needed'),
                            {'course': points_based.pk, 'target': graded.pk, 'desired_grade': 85}),
            self.client.get(reverse('planner_resource_grades_needed'),
                            {'course': points_based.pk, 'target': graded.pk, 'desired_grade': 101}),
            self.client.get(reverse('planner_resource_grades_needed'), {'course': points_based.pk}),
        ]

        # THEN
        self.assertEqual([status.HTTP_400_BAD_REQUEST] * 4, [response.status_code for response in responses])
        self.assertEqual('Select a category that is down to its last ungraded assignment.', responses[0].data['target'])
        self.assertEqual('Select an ungraded assignment in this class.', responses[1].data['target'])
        self.assertEqual('Enter a valid grade between 0 and 100.', responses[2].data['desired_grade'])
        self.assertEqual(["'course', 'target', 'desired_grade', and 'desired_gpa' must be given as numbers"],
                         responses[3].data)

    def test_needed_grade_for_a_gpa_solves_for_the_lowest_band_that_reaches_it(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user)

        # WHEN
        response = self._get_needed(course, project, desired_gpa=3.35)
        same_as_grade = self._get_needed(course, project, desired_grade=90)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({'min_grade': 90.0, 'grade_point': 3.7, 'label': 'A-'}, _floats(response.data['grade_band']),
                         'the other class is a B (3.0), so (3.0 + x) / 2 >= 3.35 needs x >= 3.7, an A-')
        self.assertEqual('achievable', response.data['state'])
        self.assertAlmostEqual(same_as_grade.data['needed_grade'], response.data['needed_grade'], places=4)
        self.assertEqual(project.pk, response.data['assignment']['id'])
        self.assertIsNone(same_as_grade.data['grade_band'])

    def test_needed_grade_for_a_gpa_counts_the_gpa_as_displayed(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user, other_grade=85, other_credits=1, credits=3)

        # WHEN
        response = self._get_needed(course, project, desired_gpa=3.53)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(3.7, float(response.data['grade_band']['grade_point']),
                         '(3.0 + 3 × 3.7) / 4 = 3.525 shows as 3.53, so an A- reaches it')

    def test_needed_grade_for_an_out_of_reach_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user)

        # WHEN
        response = self._get_needed(course, project, desired_gpa=3.9)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual('gpa_unreachable', response.data['state'])
        self.assertEqual({'min_grade': 97.0, 'grade_point': 4.0, 'label': 'A+'}, _floats(response.data['grade_band']),
                         'even an A+ (4.0) only brings (3.0 + 4.0) / 2 to 3.5')
        self.assertEqual(0, response.data['needed_grade'])
        self.assertIsNone(response.data['assignment'])

    def test_needed_grade_for_a_gpa_already_reached(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user)

        # WHEN
        response = self._get_needed(course, project, desired_gpa=1.5)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(0.0, float(response.data['grade_band']['min_grade']), 'even an F (0.0) keeps the GPA at 1.5')
        self.assertEqual('above_target', response.data['state'])

    def test_needed_grade_for_a_gpa_on_a_scale_where_lower_is_better(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user, grade_scale_template=enums.GRADE_SCALE_1_5_PASS_50)

        # WHEN
        response = self._get_needed(course, project, desired_gpa=1.5)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(90.0, float(response.data['grade_band']['min_grade']),
                         'the other class earns 1.7, so (1.7 + x) / 2 <= 1.5 needs x <= 1.3, from 90%')

    def test_needed_grade_for_a_gpa_uses_the_class_grade_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user, class_grade_scale_template=enums.GRADE_SCALE_4_0)

        # WHEN
        response = self._get_needed(course, project, desired_gpa=3.35)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({'min_grade': 90.0, 'grade_point': 4.0, 'label': 'A'}, _floats(response.data['grade_band']),
                         'on whole letters, the lowest band at or above 3.7 is an A')

    def test_needed_grade_for_a_gpa_refuses_invalid_requests(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course, project = self._given_class_to_plan_for_gpa(user)
        no_credits, no_credits_project = self._given_class_to_plan_for_gpa(user, credits=0)
        no_scale, no_scale_project = self._given_class_to_plan_for_gpa(user,
                                                                        grade_scale_template=enums.GRADE_SCALE_NONE)

        # WHEN
        responses = [
            self._get_needed(no_credits, no_credits_project, desired_gpa=3.0),
            self._get_needed(no_scale, no_scale_project, desired_gpa=3.0),
            self._get_needed(course, project, desired_gpa=3.0, desired_grade=90),
            self._get_needed(course, project),
            self._get_needed(course, project, desired_gpa=-1),
            self._get_needed(course, project, desired_gpa='nan'),
        ]

        # THEN
        self.assertEqual([status.HTTP_400_BAD_REQUEST] * 6, [response.status_code for response in responses])
        self.assertEqual('Add credits to this class to plan for a GPA.', responses[0].data['desired_gpa'])
        self.assertEqual("Set a grade scale on the class's group to plan for a GPA.", responses[1].data['desired_gpa'])
        self.assertEqual(["Only one of 'desired_grade' or 'desired_gpa' may be given."], responses[2].data)
        self.assertEqual(["One of 'desired_grade' or 'desired_gpa' must be given."], responses[3].data)
        self.assertEqual('Enter a valid GPA.', responses[4].data['desired_gpa'])
        self.assertEqual('Enter a valid GPA.', responses[5].data['desired_gpa'])

    def test_needed_grade_for_another_users_class_is_not_found(self):
        # GIVEN
        other = userhelper.given_a_user_exists(username='other', email='other@heliumedu.com')
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(other))
        exams = categoryhelper.given_category_exists(course, title='Exams', weight=100)
        homeworkhelper.given_homework_exists(course, category=exams, current_grade='-1/100')
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(reverse('planner_resource_grades_needed'),
                                   {'course': course.pk, 'target': exams.pk, 'desired_grade': 85})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_grades_includes_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        graded = coursehelper.given_graded_course_exists(course_group, 85, credits=3)
        ungraded = coursehelper.given_course_exists(course_group, credits=4)

        # WHEN
        response = self.client.get(reverse('planner_resource_grades'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_group_data = response.data['course_groups'][0]
        self.assertEqual(course_group_data['gpa'], 3.0)
        self.assertEqual(course_group_data['grade_scale'],
                         enums.GRADE_SCALE_TEMPLATES[enums.GRADE_SCALE_4_0]['scale'])
        self.assertTrue(course_group_data['in_cumulative_gpa'])
        courses = {course['id']: course for course in course_group_data['courses']}
        self.assertEqual(courses[graded.pk]['credits'], 3)
        self.assertEqual(courses[graded.pk]['grade_point'], 3.0)
        self.assertEqual(courses[ungraded.pk]['grade_point'], -1)
        self.assertEqual(response.data['cumulative_gpa'], 3.0)

    def test_get_grades_includes_each_class_grade_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(
            user, grade_scale_template=enums.GRADE_SCALE_4_0_PLUS_MINUS)
        on_group_scale = coursehelper.given_graded_course_exists(course_group, 91, credits=3)
        whole_letter = coursehelper.given_graded_course_exists(course_group, 91, credits=3,
                                                                grade_scale_template=enums.GRADE_SCALE_4_0)

        # WHEN
        response = self.client.get(reverse('planner_resource_grades'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        courses = {course['id']: course for course in response.data['course_groups'][0]['courses']}
        self.assertIsNone(courses[on_group_scale.pk]['grade_scale_template'])
        self.assertEqual(_as_floats(courses[on_group_scale.pk]['grade_scale']),
                         enums.GRADE_SCALE_TEMPLATES[enums.GRADE_SCALE_4_0_PLUS_MINUS]['scale'])
        self.assertEqual(float(courses[on_group_scale.pk]['grade_point']), 3.7)
        self.assertEqual(courses[whole_letter.pk]['grade_scale_template'], enums.GRADE_SCALE_4_0)
        self.assertEqual(_as_floats(courses[whole_letter.pk]['grade_scale']),
                         enums.GRADE_SCALE_TEMPLATES[enums.GRADE_SCALE_4_0]['scale'])
        self.assertEqual(courses[whole_letter.pk]['grade_point'], 4.0)

    def test_cumulative_gpa_pools_classes_of_groups_on_the_most_recent_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        fall = coursegrouphelper.given_course_group_exists(user, title='Fall', start_date=datetime.date(2017, 8, 21))
        spring = coursegrouphelper.given_course_group_exists(user, title='Spring', start_date=datetime.date(2018, 1, 8))
        abroad = coursegrouphelper.given_course_group_exists(user, title='Abroad',
                                                             start_date=datetime.date(2017, 5, 1),
                                                             grade_scale_template=enums.GRADE_SCALE_4_5)
        example = coursegrouphelper.given_course_group_exists(user, title='Example',
                                                              start_date=datetime.date(2019, 1, 1),
                                                              example_schedule=True)
        coursehelper.given_graded_course_exists(fall, 95, credits=3)
        coursehelper.given_graded_course_exists(spring, 85, credits=1)
        coursehelper.given_graded_course_exists(abroad, 60, credits=4)
        coursehelper.given_graded_course_exists(example, 60, credits=4)

        # WHEN
        response = self.client.get(reverse('planner_resource_grades'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_groups = {course_group['title']: course_group for course_group in response.data['course_groups']}
        self.assertEqual(course_groups['Fall']['gpa'], 4.0)
        self.assertEqual(course_groups['Spring']['gpa'], 3.0)
        self.assertEqual({title: course_group['in_cumulative_gpa'] for title, course_group in course_groups.items()},
                         {'Fall': True, 'Spring': True, 'Abroad': False, 'Example': False})
        self.assertEqual({title: course_group['example_schedule'] for title, course_group in course_groups.items()},
                         {'Fall': False, 'Spring': False, 'Abroad': False, 'Example': True})
        self.assertEqual(response.data['cumulative_gpa'], 3.75)

    def test_cumulative_gpa_without_groups(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(reverse('planner_resource_grades'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course_groups'], [])
        self.assertEqual(response.data['cumulative_gpa'], -1)

    def test_no_gpa_without_credits(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        graded = coursehelper.given_graded_course_exists(course_group, 85)

        # WHEN
        response = self.client.get(reverse('planner_resource_grades'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_group_data = response.data['course_groups'][0]
        self.assertEqual(course_group_data['gpa'], -1)
        self.assertEqual(course_group_data['courses'][0]['id'], graded.pk)
        self.assertEqual(course_group_data['courses'][0]['grade_point'], 3.0)
        self.assertEqual(response.data['cumulative_gpa'], -1)


def _as_floats(grade_scale):
    return [_floats(band) for band in grade_scale]


def _floats(grade_band):
    return {**grade_band, 'min_grade': float(grade_band['min_grade']),
            'grade_point': float(grade_band['grade_point'])}
