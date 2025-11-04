__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.19"

import logging

from django.db.models import F

from helium.common.utils import commonutils
from helium.planner.models import CourseGroup, Course, Category, Homework

logger = logging.getLogger(__name__)


def get_grade_points_for_course_group(course_group_id):
    has_weighted_grading = False
    for course in Course.objects.for_course_group(course_group_id):
        if course.has_weighted_grading:
            has_weighted_grading = True
            break

    query_set = (Homework.objects.for_course_group(course_group_id)
                 .graded()
                 .annotate(weight=F('category__weight'),
                           credits=F('course__credits'),
                           grade=F('current_grade'))
                 .values('id',
                         'title',
                         'category',
                         'credits',
                         'weight',
                         'credits',
                         'start',
                         'grade'))

    return get_grade_points_for(query_set, has_weighted_grading)


def get_grade_points_for_course(course_id):
    has_weighted_grading = Course.objects.has_weighted_grading(course_id)
    query_set = (Homework.objects.for_course(course_id)
                 .graded()
                 .annotate(weight=F('category__weight'),
                           grade=F('current_grade'))
                 .values('id',
                         'title',
                         'category',
                         'weight',
                         'start',
                         'grade'))

    return get_grade_points_for(query_set, has_weighted_grading)


def get_grade_points_for_category(category_id, average=False):
    if not average:
        has_weighted_grading = Category.objects.get(pk=category_id).weight > 0
    else:
        has_weighted_grading = False

    query_set = (Homework.objects
                 .for_category(category_id)
                 .graded()
                 .annotate(grade=F('current_grade'))
                 .values('id',
                         'title',
                         'category',
                         'start',
                         'grade'))

    return get_grade_points_for(query_set, has_weighted_grading)


def get_grade_points_for(query_set, has_weighted_grading):
    total_earned = 0
    total_possible = 0
    grade_series = []
    for item in query_set:
        earned, possible = item['grade'].split('/')
        earned = float(earned)
        possible = float(possible)
        grade = (earned / possible) * 100
        # Formula for weighted grading: ( w1xg1 + w2xg2 + w3xg3 ... ) / ( w1 + w2 + w3 ... )
        if has_weighted_grading:
            # If no weight is present, this category is ungraded
            if 'weight' not in item or not item['weight']:
                continue

            earned = (((earned / possible) * (float(item['weight']) / 100)) * 100)
            possible = float(item['weight'])

        total_earned += earned
        total_possible += possible

        grade_series.append([item['start'], round((total_earned / total_possible * 100), 4),
                             item['id'], item['title'], round(grade, 4), item.get('category', None)])

    return grade_series


def get_grade_data(user_id):
    course_groups = (CourseGroup.objects
                     .for_user(user_id)
                     .values('id',
                             'title',
                             'overall_grade',
                             'trend'))

    for course_group in course_groups:
        course_group['num_homework_graded'] = (Course.objects
                                               .for_course_group(course_group['id'])
                                               .num_homework_graded())
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


def recalculate_course_group_grade(course_group_id):
    # has_credit_grading = False
    # for course in Course.objects.for_course_group(course_group_id):
    #     if course.credits > 0:
    #         has_credit_grading = True
    #         break
    #
    # query_set = (Course.objects.for_course_group(course_group_id)
    #              .annotate(grade=Concat(F('current_grade'), Value("/100"), output_field=CharField()),
    #                        start=F('start_date'))
    #              .values('id',
    #                      'title',
    #                      'credits',
    #                      'start',
    #                      'grade'))

    # if has_credit_grading:
    #     # If no credits are present, this course is ungraded
    #     if 'credits' not in item or not item['credits']:
    #         continue
    #
    #     # Formula is same as weighted: ( cl1xcr1 + cl2xcr2 + cl3xcr3 ... ) / ( cr1 + cr2 + cr3 ... )
    #     earned = (((earned / possible) * (float(item['credits']) / 100)) * 100)
    #     possible = float(item['credits'])

    course_grade_points = [(points[1] / 100) for points in get_grade_points_for(query_set, False, has_credit_grading) if points]
    overall_grade = course_grade_points[-1] * 100 if len(course_grade_points) > 0 else -1
    trend = commonutils.calculate_trend(range(len(course_grade_points)), course_grade_points)

    course_grades = (Course.objects
                     .for_course_group(course_group_id)
                     .graded()
                     .values_list('current_grade', flat=True))
    total = sum(course_grades)
    overall_grade = total / len(course_grades) if len(course_grades) > 0 else -1
    grade_points = [(points[1] / 100) for points in get_grade_points_for_course_group(course_group_id) if points]
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Course Group {course_group_id} overall grade recalculated to '
                 f'{overall_grade} with {len(grade_points)} homework '
                 f'in {len(course_grades)} courses')
    logger.debug(f'Course Group {course_group_id} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    CourseGroup.objects.filter(pk=course_group_id).update(overall_grade=overall_grade, trend=trend)


def recalculate_course_grade(course_id):
    grade_points = [(points[1] / 100) for points in get_grade_points_for_course(course_id) if points]
    current_grade = grade_points[-1] * 100 if len(grade_points) > 0 else -1
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Course {course_id} current grade recalculated to {current_grade} '
                 f'with {len(grade_points)} homework')
    logger.debug(f'Course {course_id} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    Course.objects.filter(pk=course_id).update(current_grade=current_grade, trend=trend)

    # Also recalculate category weight breakdown
    total_earned = 0
    total_possible = 0
    category_totals = {}
    for category_id, grade, weight in (Homework.objects
            .for_course(course_id)
            .graded()
            .values_list('category_id',
                         'current_grade',
                         'category__weight')):

        earned, possible = grade.split('/')
        earned = float(earned)
        possible = float(possible)

        total_earned += earned
        total_possible += possible

        if category_id not in category_totals:
            category_totals[category_id] = {'weight': weight, 'total_earned': 0, 'total_possible': 0}

        category_totals[category_id]['total_earned'] += earned
        category_totals[category_id]['total_possible'] += possible

    for category_id, totals in category_totals.items():
        if totals['weight']:
            grade_by_weight = (((totals['total_earned'] / totals['total_possible']) * (
                    float(totals['weight']) / 100)) * 100)

            logger.debug(f'Course triggered category {category_id} '
                         f'recalculation of grade_by_weight to {grade_by_weight}')

            # Update the values in the datastore, circumventing signals
            Category.objects.filter(pk=category_id).update(grade_by_weight=grade_by_weight)


def recalculate_category_grade(category_id):
    total_earned = 0
    total_possible = 0
    for grade in Homework.objects.for_category(category_id).graded().values_list('current_grade', flat=True):
        earned, possible = grade.split('/')
        total_earned += float(earned)
        total_possible += float(possible)
    average_grade = (total_earned / total_possible) * 100 if total_possible > 0 else -1

    grade_points = [(points[1] / 100) for points in get_grade_points_for_category(category_id, average=True) if points]
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Category {category_id} average grade recalculated to '
                 f'{average_grade} with {len(grade_points)} homework')
    logger.debug(f'Category {category_id} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    Category.objects.filter(pk=category_id).update(average_grade=average_grade, trend=trend)
