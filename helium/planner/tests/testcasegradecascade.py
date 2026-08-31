import json

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Category, Course, CourseGroup
from helium.planner.services import gradingservice
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, coursehelper, homeworkhelper


class TestCaseGradeCascade(APITestCase):
    def _recalculated_from_scratch(self, user):
        for category in Category.objects.for_user(user.pk):
            gradingservice.recalculate_category_grade(category.pk)
        for course in Course.objects.for_user(user.pk):
            gradingservice.recalculate_course_grade(course.pk)
        for course_group in CourseGroup.objects.for_user(user.pk):
            gradingservice.recalculate_course_group_grade(course_group.pk)

    def assert_grades_are_not_stale(self, user, course_group=None, course=None, category=None):
        persisted = (
            CourseGroup.objects.filter(pk=course_group.pk).values_list('overall_grade', flat=True).first()
            if course_group else None,
            Course.objects.filter(pk=course.pk).values_list('current_grade', flat=True).first()
            if course else None,
            Category.objects.filter(pk=category.pk).values_list('average_grade', flat=True).first()
            if category else None,
        )

        self._recalculated_from_scratch(user)

        truth = (
            CourseGroup.objects.filter(pk=course_group.pk).values_list('overall_grade', flat=True).first()
            if course_group else None,
            Course.objects.filter(pk=course.pk).values_list('current_grade', flat=True).first()
            if course else None,
            Category.objects.filter(pk=category.pk).values_list('average_grade', flat=True).first()
            if category else None,
        )

        self.assertEqual(persisted, truth)

    def given_graded_course(self, course_group, title='🧪 Test Course', grade='90/100', count=3):
        course = coursehelper.given_course_exists(course_group, title=title)
        category = categoryhelper.given_category_exists(course, title=f'{title} category', weight=100)
        for _ in range(count):
            homeworkhelper.given_homework_exists(course, category=category, current_grade=grade,
                                                 completed=True)
        return course, category

    def test_deleting_a_course_leaves_its_course_group_grade_correct(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        kept, _ = self.given_graded_course(course_group, title='kept', grade='90/100')
        dropped, _ = self.given_graded_course(course_group, title='dropped', grade='10/100')

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_detail',
                                              kwargs={'course_group': course_group.pk, 'pk': dropped.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assert_grades_are_not_stale(user, course_group=course_group, course=kept)

    def test_deleting_a_category_leaves_its_course_grade_correct(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        kept = categoryhelper.given_category_exists(course, title='kept', weight=50)
        dropped = categoryhelper.given_category_exists(course, title='dropped', weight=50)
        for _ in range(3):
            homeworkhelper.given_homework_exists(course, category=kept, current_grade='90/100',
                                                 completed=True)
            homeworkhelper.given_homework_exists(course, category=dropped, current_grade='10/100',
                                                 completed=True)

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                              kwargs={'course_group': course_group.pk,
                                                      'course': course.pk, 'pk': dropped.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assert_grades_are_not_stale(user, course_group=course_group, course=course,
                                         category=kept)

    def test_deleting_a_category_moves_its_homework_without_losing_it(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        categoryhelper.given_category_exists(course, title='kept', weight=50)
        dropped = categoryhelper.given_category_exists(course, title='dropped', weight=50)
        for _ in range(3):
            homeworkhelper.given_homework_exists(course, category=dropped, current_grade='90/100',
                                                 completed=True)

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                              kwargs={'course_group': course_group.pk,
                                                      'course': course.pk, 'pk': dropped.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        uncategorized = Category.objects.for_course(course.pk).get(title='Uncategorized')
        self.assertEqual(uncategorized.homework.count(), 3)
        self.assert_grades_are_not_stale(user, course_group=course_group, course=course,
                                         category=uncategorized)

    def test_deleting_a_course_group_leaves_a_sibling_untouched(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        dropped_group = coursegrouphelper.given_course_group_exists(user)
        self.given_graded_course(dropped_group, title='dropped', grade='10/100')
        kept_group = coursegrouphelper.given_course_group_exists(user, title='🍁 Kept')
        kept_course, kept_category = self.given_graded_course(kept_group, title='kept',
                                                              grade='90/100')

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_detail',
                                              kwargs={'pk': dropped_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CourseGroup.objects.filter(pk=dropped_group.pk).exists())
        self.assert_grades_are_not_stale(user, course_group=kept_group, course=kept_course,
                                         category=kept_category)

    def test_moving_homework_between_categories_leaves_both_correct(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        source = categoryhelper.given_category_exists(course, title='source', weight=50)
        target = categoryhelper.given_category_exists(course, title='target', weight=50)
        moved = homeworkhelper.given_homework_exists(course, category=source,
                                                     current_grade='10/100', completed=True)
        homeworkhelper.given_homework_exists(course, category=source, current_grade='90/100',
                                             completed=True)
        homeworkhelper.given_homework_exists(course, category=target, current_grade='90/100',
                                             completed=True)

        # WHEN
        response = self.client.patch(
            reverse('planner_coursegroups_courses_homework_detail',
                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': moved.pk}),
            json.dumps({'category': target.pk}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_grades_are_not_stale(user, course_group=course_group, course=course,
                                         category=source)
        self.assert_grades_are_not_stale(user, course_group=course_group, course=course,
                                         category=target)

    def test_a_cascading_delete_does_not_recalculate_per_row(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        for index in range(3):
            self.given_graded_course(course_group, title=f'course {index}', count=10)

        # WHEN
        with CaptureQueriesContext(connection) as queries:
            response = self.client.delete(reverse('planner_coursegroups_detail',
                                                  kwargs={'pk': course_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # This deletes in ~114; recalculating per deleted row takes ~328. The ceiling sits
        # between them, clear of both an incidental query change and a false pass
        self.assertLess(len(queries), 200)
