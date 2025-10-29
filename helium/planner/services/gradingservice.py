__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.16"

import logging

from helium.common.utils import commonutils
from helium.planner.models import CourseGroup, Course, Category, Homework

logger = logging.getLogger(__name__)


def get_grade_points_for_course(course_id):
    has_weighted_grading = Course.objects.has_weighted_grading(course_id)
    query_set = (Homework.objects.for_course(course_id)
                 .graded()
                 .values_list('id',
                              'title',
                              'category_id',
                              'start',
                              'current_grade'))

    return get_grade_points_for(query_set, has_weighted_grading)


def get_grade_points_for_course_group(course_group_id):
    has_weighted_grading = False
    for course in Course.objects.for_course_group(course_group_id):
        if course.has_weighted_grading:
            has_weighted_grading = True
            break

    query_set = (Homework.objects.for_course_group(course_group_id)
                 .graded()
                 .values_list('id',
                              'title',
                              'category_id',
                              'start',
                              'current_grade'))

    return get_grade_points_for(query_set, has_weighted_grading)


def get_grade_points_for_category(category_id):
    query_set = (Homework.objects
                 .for_category(category_id)
                 .graded()
                 .values_list('id',
                              'title',
                              'category_id',
                              'start',
                              'current_grade'))

    # When fetching grade points for a single category, weighted grading does not need to be considered,
    # since the grades are not in relation to anything outside of the single category
    return get_grade_points_for(query_set, False)


def get_grade_points_for(query_set, has_weighted_grading):
    total_earned = 0
    total_possible = 0
    # Maintain grades by category as we iterate over all homework
    categories = {}
    category_totals = {}
    grade_series = []
    for homework_id, homework_title, category_id, start, current_grade in query_set:
        if category_id not in categories:
            # The category may no longer exist by the time a recalculation request is processed
            try:
                categories[category_id] = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                continue
        category = categories[category_id]

        earned, possible = current_grade.split('/')
        earned = float(earned)
        possible = float(possible)
        homework_grade = (earned / possible) * 100
        # Formula for weighted grading: weighted_grade = ( w1xg1 + w2xg2 + w3xg3 ... ) / ( w1 + w2 + w3 ... )
        if has_weighted_grading:
            # If no weight is present, this category is ungraded
            if category.weight == 0:
                continue

            if category.pk not in category_totals:
                category_totals[category.pk] = {'category': category, 'total_earned': 0, 'total_possible': 0}

            category_totals[category.pk]['total_earned'] += earned
            category_totals[category.pk]['total_possible'] += possible

            total_earned += (((earned / possible) * (float(category.weight) / 100)) * 100)
            total_possible += float(category.weight)
        else:
            total_earned += earned
            total_possible += possible

        grade_series.append([start, round((total_earned / total_possible * 100), 4), homework_id, homework_title,
                             round(homework_grade, 4), category.pk])

    return grade_series


def get_grade_data(user_id):
    course_groups = (CourseGroup.objects
                     .for_user(user_id)
                     .values('id',
                             'title',
                             'average_grade',
                             'trend'))

    for course_group in course_groups:
        course_group['overall_grade'] = course_group['average_grade']
        course_group['num_homework_graded'] = (Course.objects
                                               .for_course_group(course_group['id'])
                                               .num_homework_graded())
        course_group.pop('average_grade')
        course_group['grade_points'] = get_grade_points_for_course_group(course_group['id'])

        course_group['courses'] = (Course.objects.for_user(user_id)
                                   .for_course_group(course_group['id'])
                                   .values('id',
                                           'title',
                                           'color',
                                           'current_grade',
                                           'trend'))
        course_group_num_homework = 0
        for course in course_group['courses']:
            course_db_entity = Course.objects.filter(pk=course['id'])
            course['overall_grade'] = course['current_grade']
            course['num_homework'] = course_db_entity.num_homework()
            course_group_num_homework += course['num_homework']
            course['num_homework_graded'] = course_db_entity.num_homework_graded()
            course['has_weighted_grading'] = Course.objects.has_weighted_grading(course['id'])
            course.pop('current_grade')
            course['grade_points'] = get_grade_points_for_course(course['id'])

            course['categories'] = (Category.objects.for_user(user_id)
                                    .for_course(course['id'])
                                    .values('id',
                                            'title',
                                            'weight',
                                            'color',
                                            'average_grade',
                                            'grade_by_weight',
                                            'trend'))

            for category in course['categories']:
                category_db_entity = Category.objects.filter(pk=category['id'])
                category['overall_grade'] = category['average_grade']
                category['num_homework'] = category_db_entity.num_homework()
                category['num_homework_graded'] = category_db_entity.num_homework_graded()
                category.pop('average_grade')
                category['grade_points'] = get_grade_points_for_category(category['id'])

        course_group['num_homework'] = course_group_num_homework

    return {
        'course_groups': course_groups
    }


def recalculate_course_group_grade(course_group):
    course_grades = (Course.objects
                     .for_course_group(course_group.pk)
                     .graded()
                     .values_list('current_grade', flat=True))
    total = sum(course_grades)
    average_grade = total / len(course_grades) if len(course_grades) > 0 else -1

    grade_points = [(points[1] / 100) for points in get_grade_points_for_course_group(course_group.pk) if points]
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Course Group {course_group.pk} average grade recalculated to '
                 f'{average_grade} with {len(grade_points)} homework '
                 f'in {len(course_grades)} courses')
    logger.debug(f'Course Group {course_group.pk} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    CourseGroup.objects.filter(pk=course_group.pk).update(average_grade=average_grade, trend=trend)


def recalculate_course_grade(course):
    # Recalculate category weight breakdown
    total_earned = 0
    total_possible = 0
    # Maintain grades by category as we iterate over all homework
    category_totals = {}
    for category_id, grade in (Homework.objects
            .for_course(course.pk)
            .graded()
            .values_list('category_id',
                         'current_grade')):
        # The category may no longer exist by the time a recalculation request is processed
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            continue

        earned, possible = grade.split('/')
        earned = float(earned)
        possible = float(possible)

        total_earned += earned
        total_possible += possible

        if category.pk not in category_totals:
            category_totals[category.pk] = {'instance': category, 'total_earned': 0, 'total_possible': 0}

        category_totals[category.pk]['total_earned'] += earned
        category_totals[category.pk]['total_possible'] += possible

    category_earned = 0
    category_possible = 0
    for category in category_totals.values():
        if course.has_weighted_grading:
            grade_by_weight = (((category['total_earned'] / category['total_possible']) * (
                    float(category['instance'].weight) / 100)) * 100)

            category_earned += grade_by_weight
            category_possible += float(category['instance'].weight)

            logger.debug(f'Course triggered category {category["instance"].pk} '
                         f'recalculation of grade_by_weight to {grade_by_weight}')
        else:
            category_earned += total_earned
            category_possible += total_possible

            grade_by_weight = 0

        # Update the values in the datastore, circumventing signals
        Category.objects.filter(pk=category['instance'].pk).update(grade_by_weight=grade_by_weight)

    # Recalculate course grade
    grade_points = [(points[1] / 100) for points in get_grade_points_for_course(course.pk) if points]
    current_grade = grade_points[-1] * 100 if len(grade_points) > 0 else -1
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Course {course.pk} current grade recalculated to {current_grade} '
                 f'with {len(grade_points)} homework')
    logger.debug(f'Course {course.pk} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    Course.objects.filter(pk=course.pk).update(current_grade=current_grade, trend=trend)


def recalculate_category_grade(category):
    total_earned = 0
    total_possible = 0
    for grade in Homework.objects.for_category(category.pk).graded().values_list('current_grade', flat=True):
        earned, possible = grade.split('/')
        total_earned += float(earned)
        total_possible += float(possible)
    average_grade = (total_earned / total_possible) * 100 if total_possible > 0 else -1

    grade_points = [(points[1] / 100) for points in get_grade_points_for_category(category.pk) if points]
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Category {category.pk} average grade recalculated to '
                 f'{average_grade} with {len(grade_points)} homework')
    logger.debug(f'Category {category.pk} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    Category.objects.filter(pk=category.pk).update(average_grade=average_grade, trend=trend)
