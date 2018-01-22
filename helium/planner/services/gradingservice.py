import logging

from helium.common.utils import commonutils
from helium.planner.models import CourseGroup, Course, Category, Homework

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def get_grade_points_for_course(course_id):
    course_has_weighted_grading = Course.objects.has_weighted_grading(course_id)

    total_earned = 0
    total_possible = 0
    # Maintain grades by category as we iterate over all homework
    category_totals = {}
    grade_series = []
    for category_id, start, grade in Homework.objects.for_course(course_id).graded().values_list('category_id', 'start',
                                                                                                 'current_grade'):
        category = Category.objects.get(pk=category_id)

        earned, possible = grade.split('/')
        earned = float(earned)
        possible = float(possible)
        if course_has_weighted_grading:
            if category.pk not in category_totals:
                category_totals[category.pk] = {'category': category, 'total_earned': 0, 'total_possible': 0}

            category_totals[category.pk]['total_earned'] += earned
            category_totals[category.pk]['total_possible'] += float(possible)

            total_earned += (((earned / possible) * (float(category.weight) / 100)) * 100)
            total_possible += float(category.weight)
        else:
            total_earned += float(earned)
            total_possible += float(possible)

        grade_series.append([start, (total_earned / total_possible) * 100])

    return grade_series


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


def recalculate_course_group_grade(course_group):
    course_grades = Course.objects.for_course_group(course_group.pk).graded().values_list('current_grade', flat=True)
    total = sum(course_grades)

    course_group.average_grade = total / len(course_grades) if len(course_grades) > 0 else -1

    logger.debug('Course Group {} average grade recalculated to {} with {} courses'.format(course_group.pk,
                                                                                           course_group.average_grade,
                                                                                           len(course_grades)))

    homework_grades = Homework.objects.for_course_group(course_group.pk).graded().values_list('current_grade',
                                                                                              flat=True)

    total_earned = 0
    total_possible = 0
    # We could more simply sum this value, but we're maintaining a list so we can use it later to calculate the
    # linear regression
    grade_series = []
    for grade in homework_grades:
        earned, possible = grade.split('/')
        total_earned += float(earned)
        total_possible += float(possible)

        grade_series.append(total_earned / total_possible)

    course_group.trend = commonutils.calculate_trend(range(len(grade_series)), grade_series)

    logger.debug('Course Group {} trend recalculated to {}'.format(course_group.pk, course_group.trend))

    course_group.save()


def recalculate_course_grade(course):
    course_has_weighted_grading = Course.objects.has_weighted_grading(course.pk)

    total_earned = 0
    total_possible = 0
    # Maintain grades by category as we iterate over all homework
    category_totals = {}
    # We could more simply sum this value, but we're maintaining a list so we can use it later to calculate the
    # linear regression; note that this grade series is just for raw grade trend analysis and does not take weight
    # into account
    grade_series = []
    for category_id, grade in Homework.objects.for_course(course.pk).graded().values_list('category_id',
                                                                                          'current_grade'):
        category = Category.objects.get(pk=category_id)

        earned, possible = grade.split('/')
        earned = float(earned)
        possible = float(possible)

        total_earned += earned
        total_possible += possible

        grade_series.append(total_earned / total_possible)

        if category.pk not in category_totals:
            category_totals[category.pk] = {'instance': category, 'total_earned': 0, 'total_possible': 0}

        category_totals[category.pk]['total_earned'] += earned
        category_totals[category.pk]['total_possible'] += possible

    category_earned = 0
    category_possible = 0
    for category in category_totals.values():
        if course_has_weighted_grading:
            category_earned += (((category['total_earned'] / category['total_possible']) * (
                float(category['instance'].weight) / 100)) * 100)
            category_possible += float(category['instance'].weight)

            category['instance'].grade_by_weight = category_earned
        else:
            category_earned += total_earned
            category_possible += total_possible

            category['instance'].grade_by_weight = 0

        category['instance'].save()

    if len(grade_series) > 0 and category_possible > 0:
        course.current_grade = (category_earned / category_possible) * 100
    else:
        course.current_grade = -1

    course.trend = commonutils.calculate_trend(range(len(grade_series)), grade_series)

    course.save()


def recalculate_category_grade(category):
    total_earned = 0
    total_possible = 0
    # We could more simply sum this value, but we're maintaining a list so we can use it later to calculate the
    # linear regression
    grade_series = []
    for grade in Homework.objects.for_category(category.pk).graded().values_list('current_grade', flat=True):
        earned, possible = grade.split('/')
        total_earned += float(earned)
        total_possible += float(possible)

        grade_series.append(total_earned / total_possible)

    category.average_grade = (total_earned / total_possible) * 100 if len(grade_series) > 0 else -1

    category.trend = commonutils.calculate_trend(range(len(grade_series)), grade_series)

    category.save()

    logger.debug('Category {} average grade recalculated to {} with {} homework'.format(category.pk,
                                                                                        category.average_grade,
                                                                                        len(grade_series)))
