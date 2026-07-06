__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

# Grading math is also implemented in the frontend at
# projects/frontend/lib/utils/grade_helpers.dart. The frontend operates on
# category aggregates produced by this service (it does NOT recompute course
# grades from raw homework — those come from here). The "What Grade Do I Need?"
# inverse calculation is frontend-only. If you change the weighted-grade math
# here, audit grade_helpers.dart for consistency. Both sides have their own
# test suites covering the math at their respective layers.

import logging

from django.db.models import F, Count, Q, Case, When, Exists, OuterRef, FloatField, Value

from helium.common.utils import commonutils
from helium.planner.models import CourseGroup, Course, Category, Homework

logger = logging.getLogger(__name__)


def get_grade_points_for_course_group(course_group_id):
    course_grade_points = []
    # Fetch grade points for each course in the group, then sort by date
    # Annotate has_weighted_grading to avoid N+1 queries
    courses = (Course.objects.for_course_group(course_group_id)
               .annotate(annotated_has_weighted_grading=Exists(
                   Category.objects.filter(course_id=OuterRef('pk'), weight__gt=0)
               )))
    for course in courses:
        course_grade_points += get_grade_points_for_course(course.id, course.annotated_has_weighted_grading)
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


def get_grade_points_for_course(course_id, has_weighted_grading=None):
    if has_weighted_grading is None:
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


def get_homework_series_for_course(course_id, has_weighted_grading=None):
    if has_weighted_grading is None:
        has_weighted_grading = Course.objects.has_weighted_grading(course_id)
    grade_points = get_grade_points_for_course(course_id, has_weighted_grading)
    categories = list(Category.objects.for_course(course_id)
                      .annotate(
                          annotated_num_homework=Count('homework', distinct=True),
                          annotated_num_homework_graded=Count(
                              'homework',
                              filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'),
                              distinct=True
                          )
                      )
                      .values('id', 'weight', 'average_grade',
                              'annotated_num_homework', 'annotated_num_homework_graded'))
    cat_dicts = []
    for cat in categories:
        cat_dicts.append({
            'id': cat['id'],
            'weight': cat['weight'],
            'overall_grade': cat['average_grade'],
            'num_homework': cat['annotated_num_homework'],
            'num_homework_graded': cat['annotated_num_homework_graded'],
        })
    raw_ungraded = list(Homework.objects
                        .for_course(course_id)
                        .filter(current_grade='-1/100')
                        .order_by('start')
                        .values('id', 'title', 'start', 'course_id', 'category_id', 'current_grade'))
    return _build_homework_series(grade_points, has_weighted_grading, cat_dicts, raw_ungraded)


def get_grade_points_for(query_set, has_weighted_grading):
    total_earned = 0
    total_possible = 0
    grade_series = []
    for item in query_set:
        earned, possible = item['grade'].split('/')
        earned = float(earned)
        possible = float(possible)
        if possible <= 0:
            logger.warning(f'Skipping Homework {item["id"]} with non-positive denominator in current_grade')
            continue
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
                             'annotated_num_homework_graded')
                     .order_by('start_date', 'title'))

    for course_group in course_groups:
        course_group['num_homework'] = course_group['annotated_num_homework']
        course_group['num_homework_completed'] = course_group['annotated_num_homework_completed']
        course_group['num_homework_graded'] = course_group['annotated_num_homework_graded']
        # Remove the annotated_ prefixed keys
        course_group.pop('annotated_num_homework')
        course_group.pop('annotated_num_homework_completed')
        course_group.pop('annotated_num_homework_graded')
        course_group['grade_points'] = get_grade_points_for_course_group(course_group['id'])

        # Annotate courses with homework counts and has_weighted_grading to avoid N+1 queries
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
                                       ),
                                       annotated_has_weighted_grading=Exists(
                                           Category.objects.filter(course_id=OuterRef('pk'), weight__gt=0)
                                       )
                                   )
                                   .values('id',
                                           'title',
                                           'color',
                                           'current_grade',
                                           'trend',
                                           'annotated_num_homework',
                                           'annotated_num_homework_completed',
                                           'annotated_num_homework_graded',
                                           'annotated_has_weighted_grading')
                                   .order_by('start_date', 'title'))
        # Batch-fetch all ungraded homework for this group's courses in one query
        # to avoid an N+1 when computing homework_series per course.
        ungraded_by_course = {}
        for hw in (Homework.objects
                   .filter(course__course_group_id=course_group['id'],
                           current_grade='-1/100')
                   .order_by('start')
                   .values('id', 'title', 'start', 'course_id', 'category_id', 'current_grade')):
            ungraded_by_course.setdefault(hw['course_id'], []).append(hw)

        course_group_num_homework = 0
        for course in course_group['courses']:
            course['overall_grade'] = course['current_grade']
            course['num_homework'] = course['annotated_num_homework']
            course_group_num_homework += course['num_homework']
            course['num_homework_completed'] = course['annotated_num_homework_completed']
            course['num_homework_graded'] = course['annotated_num_homework_graded']
            course['has_weighted_grading'] = course['annotated_has_weighted_grading']
            # Remove the annotated_ prefixed keys
            course.pop('annotated_num_homework')
            course.pop('annotated_num_homework_completed')
            course.pop('annotated_num_homework_graded')
            course.pop('annotated_has_weighted_grading')
            course.pop('current_grade')
            course['grade_points'] = get_grade_points_for_course(course['id'], course['has_weighted_grading'])

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
                                            'annotated_num_homework_graded')
                                    .order_by('title'))

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

            course['homework_series'] = _build_homework_series(
                course['grade_points'],
                course['has_weighted_grading'],
                list(course['categories']),
                ungraded_by_course.get(course['id'], [])
            )

            category_homework_series = {}
            for item in course['homework_series']:
                category_homework_series.setdefault(item['category_id'], []).append(item)

            for category in course['categories']:
                category['homework_series'] = category_homework_series.get(category['id'], [])

        course_group['num_homework'] = course_group_num_homework
        course_group['homework_series'] = _build_course_group_homework_series(course_group['courses'])

    return {
        'course_groups': course_groups
    }


def _build_ungraded_series_items(has_weighted_grading, categories, raw_ungraded):
    """
    Build the ungraded portion of a course's homework_series.

    Each item carries an impact_score representing the grade impact if the assignment
    is scored 100%. For non-weighted courses impact_score is None (all assignments are
    equally weighted by points). raw_ungraded must be pre-sorted by start ascending so
    that within-category ties retain the soonest-due assignment first.

    Makes no DB queries.

    :param has_weighted_grading: Whether the course uses weighted grading.
    :param categories: List of category dicts with keys id, weight, num_homework,
        num_homework_graded, overall_grade.
    :param raw_ungraded: List of homework dicts with keys id, title, start, course_id,
        category_id, current_grade.
    :return: List of homework_series item dicts with graded=False.
    """
    if not raw_ungraded:
        return []

    category_impact = {}
    if has_weighted_grading:
        for category in categories:
            weight = float(category.get('weight') or 0)
            if weight <= 0:
                continue
            if category['num_homework'] - category['num_homework_graded'] <= 0:
                continue
            num_graded = category['num_homework_graded']
            current_grade = max(0.0, float(category['overall_grade']))
            new_grade = (current_grade * num_graded + 100.0) / (num_graded + 1)
            category_impact[category['id']] = round((new_grade - current_grade) * weight / 100.0, 4)

    result = []
    for hw in raw_ungraded:
        _, possible = hw['current_grade'].split('/')
        possible = float(possible)
        if possible <= 0:
            logger.warning(f'Skipping ungraded Homework {hw["id"]} with non-positive denominator in current_grade')
            continue
        result.append({
            'id': hw['id'],
            'title': hw['title'],
            'start': hw['start'],
            'category_id': hw['category_id'],
            'course_id': hw['course_id'],
            'points_possible': possible,
            'graded': False,
            'homework_grade': None,
            'cumulative_grade': None,
            'impact_score': category_impact.get(hw['category_id']),
        })

    return result


def _build_homework_series(grade_points, has_weighted_grading, categories, raw_ungraded):
    """
    Build the course-level homework_series by combining graded items (derived from the
    legacy grade_points tuples) with ungraded items, sorted by due date ascending.

    :param grade_points: Legacy grade_points tuple list for this course.
    :param has_weighted_grading: Whether the course uses weighted grading.
    :param categories: List of category dicts (passed through to ungraded builder).
    :param raw_ungraded: Pre-sorted list of raw ungraded homework dicts.
    :return: Sorted list of homework_series item dicts.
    """
    graded = [
        {
            'id': gp[2],
            'title': gp[3],
            'start': gp[0],
            'category_id': gp[5],
            'course_id': gp[6],
            'points_possible': None,
            'graded': True,
            'homework_grade': gp[4],
            'cumulative_grade': gp[1],
            'impact_score': None,
        }
        for gp in grade_points
    ]
    ungraded = _build_ungraded_series_items(has_weighted_grading, categories, raw_ungraded)
    return sorted(graded + ungraded, key=lambda item: item['start'])


def _build_course_group_homework_series(courses):
    """
    Build course_group-level homework_series by merging per-course series and averaging
    cumulative_grade across courses at each graded point. Parallels
    get_grade_points_for_course_group() logic.

    Ungraded items pass through with cumulative_grade=None and no averaging.
    """
    all_graded = []
    all_ungraded = []
    for course in courses:
        for item in course.get('homework_series', []):
            if item['graded']:
                all_graded.append(item)
            else:
                all_ungraded.append(item)

    all_graded = sorted(all_graded, key=lambda x: x['start'])

    course_grades = {}
    series = []
    for item in all_graded:
        course_id = item['course_id']
        if course_id not in course_grades:
            course_grades[course_id] = []
        course_grades[course_id].append(item['cumulative_grade'])

        total = sum(grades[-1] for grades in course_grades.values())
        overall_grade = round(total / len(course_grades), 4)
        series.append({
            'id': item['id'],
            'title': item['title'],
            'start': item['start'],
            'category_id': item['category_id'],
            'course_id': item['course_id'],
            'points_possible': None,
            'graded': True,
            'homework_grade': item['homework_grade'],
            'cumulative_grade': overall_grade,
            'impact_score': None,
        })

    all_ungraded = sorted(all_ungraded, key=lambda x: x['start'])
    return sorted(series + all_ungraded, key=lambda item: item['start'])


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
        if possible <= 0:
            logger.warning(f'Skipping Homework in category {category_id} with non-positive denominator in current_grade')
            continue

        if category_id not in category_totals:
            category_totals[category_id] = {'weight': weight, 'total_earned': 0, 'total_possible': 0}

        category_totals[category_id]['total_earned'] += earned
        category_totals[category_id]['total_possible'] += possible

    whens = []
    for category_id, totals in category_totals.items():
        if totals['weight']:
            grade_by_weight = (((totals['total_earned'] / totals['total_possible']) * (
                    float(totals['weight']) / 100)) * 100)

            logger.debug(f'Course triggered category {category_id} '
                         f'recalculation of grade_by_weight to {grade_by_weight}')

            whens.append(When(pk=category_id, then=Value(grade_by_weight, output_field=FloatField())))

    if whens:
        Category.objects.filter(
            pk__in=[cid for cid, t in category_totals.items() if t['weight']]
        ).update(grade_by_weight=Case(*whens, output_field=FloatField()))

    Category.objects.for_course(course_id).filter(weight=0).update(grade_by_weight=0)


def recalculate_category_grade(category_id):
    total_earned = 0
    total_possible = 0
    grades = []
    for pk, grade in Homework.objects.for_category(category_id).graded().values_list('pk', 'current_grade'):
        earned, possible = grade.split('/')
        earned = float(earned)
        possible = float(possible)
        if possible <= 0:
            logger.warning(f'Skipping Homework {pk} with non-positive denominator in current_grade')
            continue
        total_earned += earned
        total_possible += possible
        grades.append(total_earned / total_possible)
    average_grade = (total_earned / total_possible) * 100 if total_possible > 0 else -1
    trend = commonutils.calculate_trend(range(len(grades)), grades)

    logger.debug(f'Category {category_id} average grade recalculated to '
                 f'{average_grade} with {len(grades)} homework')
    logger.debug(f'Category {category_id} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    Category.objects.filter(pk=category_id).update(average_grade=average_grade, trend=trend)
