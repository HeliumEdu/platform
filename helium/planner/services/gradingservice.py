import logging

from helium.planner.models import CourseGroup, Course, Category, Homework

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def get_grade_points_for_course(course_id):
    grade_points = []

    course_has_weight_grading = Course.objects.has_weighted_grading(course_id)

    for homework in Homework.objects.for_course(course_id).graded().iterator():
        # TODO: this should actually build a cumulative timeline of grading data, taking weight into account if applicable
        grade_points.append([homework.start, 0])

    return grade_points


def get_grade_data(user_id):
    course_groups = CourseGroup.objects.for_user(user_id).values('id', 'average_grade')

    for course_group in course_groups:
        course_group['overall_grade'] = course_group['average_grade']
        course_group.pop('average_grade')
        course_group['grade_points'] = []

        course_group['courses'] = Course.objects.for_user(user_id).for_course_group(course_group['id']).values('id',
                                                                                                               'current_grade')

        for course in course_group['courses']:
            course['overall_grade'] = course['current_grade']
            course.pop('current_grade')
            course['grade_points'] = get_grade_points_for_course(course['id'])

            course['categories'] = Category.objects.for_user(user_id).for_course(course['id']).values('id',
                                                                                                      'average_grade')

            for category in course['categories']:
                category['overall_grade'] = category['average_grade']
                category.pop('average_grade')
                category['grade_points'] = []

    return {
        'course_groups': course_groups
    }
