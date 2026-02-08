__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.24"

import logging

from django.db.models import F, Count, Q, Case, When

from helium.common.utils import commonutils
from helium.planner.models import CourseGroup, Course, Category, Homework

logger = logging.getLogger(__name__)


def get_grade_points_for_course_group(course_group_id):
    course_grade_points = []
    # Fetch grade points for each course in the group, then sort by date
    for course in Course.objects.for_course_group(course_group_id):
        course_grade_points += get_grade_points_for_course(course.id)
    course_grade_points = sorted(course_grade_points, key=lambda x: x[0])

    # Now average the grades of all courses as each grade point to build the group's points
    course_grades = {}
    grade_points = []
    for item in course_grade_points:
        if item[6] not in course_grades:
            course_grades[item[6]] = []
        course_grades[item[6]].append(item[1])

        sum = 0
        for course_id in course_grades.keys():
            sum += course_grades[course_id][-1]
        overall_grade = round(sum / len(course_grades.keys()), 4)
        grade_points.append([item[0],
                             overall_grade,
                             item[2],
                             item[3],
                             item[4],
                             item[5],
                             item[6]])

    return grade_points


def get_grade_points_for_course(course_id):
    has_weighted_grading = Course.objects.has_weighted_grading(course_id)
    query_set = (Homework.objects.for_course(course_id)
                 .graded()
                 .annotate(weight=F('category__weight'),
                           grade=F('current_grade'))
                 .values('id',
                         'title',
                         'category',
                         'course',
                         'weight',
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
            # If no weight present, this category is ungraded
            if 'weight' not in item or not item['weight']:
                continue

            earned = (((earned / possible) * (float(item['weight']) / 100)) * 100)
            possible = float(item['weight'])

        total_earned += earned
        total_possible += possible

        grade_series.append([item['start'],
                             round((total_earned / total_possible * 100), 4),
                             item['id'],
                             item['title'],
                             round(grade, 4),
                             item['category'],
                             item['course']])

    return grade_series


def get_grade_data(user_id):
    # Annotate course groups with homework counts to avoid N+1 queries
    course_groups = (CourseGroup.objects
                     .for_user(user_id)
                     .annotate(
                         annotated_num_homework=Count('courses__homework', distinct=True),
                         annotated_num_homework_completed=Count(
                             'courses__homework',
                             filter=Q(courses__homework__completed=True),
                             distinct=True
                         ),
                         annotated_num_homework_graded=Count(
                             'courses__homework',
                             filter=Q(courses__homework__completed=True) & ~Q(courses__homework__current_grade='-1/100'),
                             distinct=True
                         )
                     )
                     .values('id',
                             'title',
                             'overall_grade',
                             'trend',
                             'annotated_num_homework',
                             'annotated_num_homework_completed',
                             'annotated_num_homework_graded'))

    for course_group in course_groups:
        course_group['num_homework'] = course_group['annotated_num_homework']
        course_group['num_homework_completed'] = course_group['annotated_num_homework_completed']
        course_group['num_homework_graded'] = course_group['annotated_num_homework_graded']
        # Remove the annotated_ prefixed keys
        course_group.pop('annotated_num_homework')
        course_group.pop('annotated_num_homework_completed')
        course_group.pop('annotated_num_homework_graded')
        course_group['grade_points'] = get_grade_points_for_course_group(course_group['id'])

        # Annotate courses with homework counts to avoid N+1 queries
        course_group['courses'] = (Course.objects.for_user(user_id)
                                   .for_course_group(course_group['id'])
                                   .annotate(
                                       annotated_num_homework=Count('homework', distinct=True),
                                       annotated_num_homework_completed=Count(
                                           'homework',
                                           filter=Q(homework__completed=True),
                                           distinct=True
                                       ),
                                       annotated_num_homework_graded=Count(
                                           'homework',
                                           filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'),
                                           distinct=True
                                       )
                                   )
                                   .values('id',
                                           'title',
                                           'color',
                                           'current_grade',
                                           'trend',
                                           'annotated_num_homework',
                                           'annotated_num_homework_completed',
                                           'annotated_num_homework_graded'))
        course_group_num_homework = 0
        for course in course_group['courses']:
            course['overall_grade'] = course['current_grade']
            course['num_homework'] = course['annotated_num_homework']
            course_group_num_homework += course['num_homework']
            course['num_homework_completed'] = course['annotated_num_homework_completed']
            course['num_homework_graded'] = course['annotated_num_homework_graded']
            course['has_weighted_grading'] = Course.objects.has_weighted_grading(course['id'])
            # Remove the annotated_ prefixed keys
            course.pop('annotated_num_homework')
            course.pop('annotated_num_homework_completed')
            course.pop('annotated_num_homework_graded')
            course.pop('current_grade')
            course['grade_points'] = get_grade_points_for_course(course['id'])

            # Annotate categories with homework counts to avoid N+1 queries
            course['categories'] = (Category.objects.for_user(user_id)
                                    .for_course(course['id'])
                                    .annotate(
                                        annotated_num_homework=Count('homework', distinct=True),
                                        annotated_num_homework_completed=Count(
                                            'homework',
                                            filter=Q(homework__completed=True),
                                            distinct=True
                                        ),
                                        annotated_num_homework_graded=Count(
                                            'homework',
                                            filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'),
                                            distinct=True
                                        )
                                    )
                                    .values('id',
                                            'title',
                                            'weight',
                                            'color',
                                            'average_grade',
                                            'grade_by_weight',
                                            'trend',
                                            'annotated_num_homework',
                                            'annotated_num_homework_completed',
                                            'annotated_num_homework_graded'))

            category_grade_points = {}
            for grade_point in course['grade_points']:
                category_id = grade_point[5]
                if category_id not in category_grade_points:
                    category_grade_points[category_id] = []

                category_grade_points[category_id].append(grade_point)

            for category in course['categories']:
                category['overall_grade'] = category['average_grade']
                category['num_homework'] = category['annotated_num_homework']
                category['num_homework_completed'] = category['annotated_num_homework_completed']
                category['num_homework_graded'] = category['annotated_num_homework_graded']
                # Remove the annotated_ prefixed keys
                category.pop('annotated_num_homework')
                category.pop('annotated_num_homework_completed')
                category.pop('annotated_num_homework_graded')
                category.pop('average_grade')
                category['grade_points'] = category_grade_points.get(category['id'], [])

        course_group['num_homework'] = course_group_num_homework

    return {
        'course_groups': course_groups
    }


def recalculate_course_group_grade(course_group_id):
    num_courses = Course.objects.for_course_group(course_group_id).count()
    grade_points = [(points[1] / 100) for points in get_grade_points_for_course_group(course_group_id) if points]
    overall_grade = grade_points[-1] * 100 if len(grade_points) > 0 else -1
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Course Group {course_group_id} overall grade recalculated to '
                 f'{overall_grade} with {len(grade_points)} homework '
                 f'in {num_courses} courses')
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

    Category.objects.for_course(course_id).filter(weight=0).update(grade_by_weight=0)


def recalculate_category_grade(category_id):
    total_earned = 0
    total_possible = 0
    grades = []
    for grade in Homework.objects.for_category(category_id).graded().values_list('current_grade', flat=True):
        earned, possible = grade.split('/')
        total_earned += float(earned)
        total_possible += float(possible)
        grades.append(total_earned / total_possible)
    average_grade = (total_earned / total_possible) * 100 if total_possible > 0 else -1
    trend = commonutils.calculate_trend(range(len(grades)), grades)

    logger.debug(f'Category {category_id} average grade recalculated to '
                 f'{average_grade} with {len(grades)} homework')
    logger.debug(f'Category {category_id} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    Category.objects.filter(pk=category_id).update(average_grade=average_grade, trend=trend)
