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


def _get_grade_points_for_course_group(course_group_id):
    course_grade_points = []
    courses = (Course.objects.for_course_group(course_group_id)
               .annotate(annotated_has_weighted_grading=Exists(
                   Category.objects.filter(course_id=OuterRef('pk'), weight__gt=0)
               )))
    has_weighted_by_course = {course.id: course.annotated_has_weighted_grading for course in courses}
    grade_points_by_course = _get_grade_points_by_course_for_group(course_group_id, has_weighted_by_course)
    for course in courses:
        course_grade_points += grade_points_by_course.get(course.id, [])
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


def _graded_grade_point_values(homework_queryset):
    return (homework_queryset
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


def _get_grade_points_for_course(course_id, has_weighted_grading=None):
    if has_weighted_grading is None:
        has_weighted_grading = Course.objects.has_weighted_grading(course_id)
    query_set = _graded_grade_point_values(Homework.objects.for_course(course_id))

    return _get_grade_points_for(query_set, has_weighted_grading)


def _graded_items_by_course(course_group_id):
    items_by_course = {}
    for item in _graded_grade_point_values(Homework.objects.for_course_group(course_group_id)):
        items_by_course.setdefault(item['course'], []).append(item)

    return items_by_course


def _grade_points_by_course(graded_items_by_course, has_weighted_by_course):
    return {course_id: _get_grade_points_for(items, has_weighted_by_course.get(course_id, False))
            for course_id, items in graded_items_by_course.items()}


def _get_grade_points_by_course_for_group(course_group_id, has_weighted_by_course):
    return _grade_points_by_course(_graded_items_by_course(course_group_id), has_weighted_by_course)


def _add_category_points(category_totals, category_id, weight, earned, possible):
    totals = category_totals.setdefault(category_id, {'weight': float(weight), 'earned': 0, 'possible': 0})
    totals['earned'] += earned
    totals['possible'] += possible


def _weighted_course_grade(category_totals):
    weighted_grade = sum((t['earned'] / t['possible']) * t['weight'] for t in category_totals.values())
    total_weight = sum(t['weight'] for t in category_totals.values())
    return weighted_grade / total_weight * 100


def _points_totals(graded_items):
    points_earned = 0.0
    points_possible = 0.0
    for item in graded_items:
        earned, possible = item['grade'].split('/')
        if float(possible) <= 0:
            continue
        points_earned += float(earned)
        points_possible += float(possible)

    return points_earned, points_possible


def _points_totals_by_category(graded_items):
    items_by_category = {}
    for item in graded_items:
        items_by_category.setdefault(item['category'], []).append(item)

    return {category_id: _points_totals(items) for category_id, items in items_by_category.items()}


def _weighted_category_totals(graded_items):
    category_totals = {}
    for item in graded_items:
        if not item.get('weight'):
            continue
        earned, possible = item['grade'].split('/')
        if float(possible) <= 0:
            continue
        _add_category_points(category_totals, item['category'], item['weight'], float(earned), float(possible))

    return category_totals


def _get_grade_points_for(query_set, has_weighted_grading):
    total_earned = 0
    total_possible = 0
    category_totals = {}
    grade_series = []
    for item in query_set:
        earned, possible = item['grade'].split('/')
        earned = float(earned)
        possible = float(possible)
        if possible <= 0:
            logger.warning(f'Skipping Homework {item["id"]} with non-positive denominator in current_grade')
            continue
        grade = (earned / possible) * 100
        # Formula for weighted grading: ( w1xg1 + w2xg2 + w3xg3 ... ) / ( w1 + w2 + w3 ... ), where each g is a
        # category's points grade (earned / possible) and only categories with graded homework so far are included
        if has_weighted_grading:
            # If no weight present, this category is ungraded
            if 'weight' not in item or not item['weight']:
                continue

            _add_category_points(category_totals, item['category'], item['weight'], earned, possible)
            cumulative_grade = _weighted_course_grade(category_totals)
        else:
            total_earned += earned
            total_possible += possible
            cumulative_grade = total_earned / total_possible * 100

        grade_series.append([item['start'],
                             round(cumulative_grade, 4),
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
        course_group['grade_points'] = _get_grade_points_for_course_group(course_group['id'])

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

        # Batch grade points and categories for every course in one query each, rather than per course.
        has_weighted_by_course = {course['id']: course['annotated_has_weighted_grading']
                                  for course in course_group['courses']}
        graded_items_by_course = _graded_items_by_course(course_group['id'])
        grade_points_by_course = _grade_points_by_course(graded_items_by_course, has_weighted_by_course)

        categories_by_course = {}
        for category in (Category.objects.for_user(user_id)
                         .filter(course__course_group_id=course_group['id'])
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
                         .values('id', 'title', 'weight', 'color', 'average_grade', 'grade_by_weight', 'trend',
                                 'course', 'annotated_num_homework', 'annotated_num_homework_completed',
                                 'annotated_num_homework_graded')
                         .order_by('title')):
            categories_by_course.setdefault(category.pop('course'), []).append(category)

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
            course['grade_points'] = grade_points_by_course.get(course['id'], [])
            course_graded_items = graded_items_by_course.get(course['id'], [])
            course['points_earned'], course['points_possible'] = _points_totals(course_graded_items)
            points_by_category = _points_totals_by_category(course_graded_items)

            course['categories'] = categories_by_course.get(course['id'], [])

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
                category['points_earned'], category['points_possible'] = points_by_category.get(category['id'],
                                                                                                (0.0, 0.0))

            course['homework_series'] = _build_homework_series(
                course['grade_points'],
                course['has_weighted_grading'],
                list(course['categories']),
                _weighted_category_totals(graded_items_by_course.get(course['id'], [])),
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


def _build_ungraded_series_items(has_weighted_grading, categories, category_totals, raw_ungraded):
    """
    Build the ungraded portion of a course's homework_series.

    In a weighted course, each item in a weighted category carries an impact_score: how many
    points the course grade rises if the assignment is scored 100%, using the same category
    points model as the course grade. With no graded work yet, the course grade is taken as 0.
    For non-weighted courses impact_score is None (all assignments are equally weighted by
    points). raw_ungraded must be pre-sorted by start ascending so that ties retain the
    soonest-due assignment first.

    Makes no DB queries.

    :param has_weighted_grading: Whether the course uses weighted grading.
    :param categories: List of category dicts with keys id and weight.
    :param category_totals: The course's graded points per weighted category, as built by
        _weighted_category_totals().
    :param raw_ungraded: List of homework dicts with keys id, title, start, course_id,
        category_id, current_grade.
    :return: List of homework_series item dicts with graded=False.
    """
    if not raw_ungraded:
        return []

    weights = {}
    current_grade = 0.0
    if has_weighted_grading:
        weights = {category['id']: float(category.get('weight') or 0) for category in categories}
        if category_totals:
            current_grade = _weighted_course_grade(category_totals)

    result = []
    for hw in raw_ungraded:
        _, possible = hw['current_grade'].split('/')
        possible = float(possible)
        if possible <= 0:
            logger.warning(f'Skipping ungraded Homework {hw["id"]} with non-positive denominator in current_grade')
            continue
        impact_score = None
        weight = weights.get(hw['category_id'], 0)
        if weight > 0:
            projected_totals = {category_id: dict(totals) for category_id, totals in category_totals.items()}
            _add_category_points(projected_totals, hw['category_id'], weight, possible, possible)
            impact_score = round(_weighted_course_grade(projected_totals) - current_grade, 4)
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
            'impact_score': impact_score,
        })

    return result


def _build_homework_series(grade_points, has_weighted_grading, categories, category_totals, raw_ungraded):
    """
    Build the course-level homework_series by combining graded items (derived from the
    legacy grade_points tuples) with ungraded items, sorted by due date ascending.

    :param grade_points: Legacy grade_points tuple list for this course.
    :param has_weighted_grading: Whether the course uses weighted grading.
    :param categories: List of category dicts (passed through to ungraded builder).
    :param category_totals: Graded points per weighted category (passed through to ungraded builder).
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
    ungraded = _build_ungraded_series_items(has_weighted_grading, categories, category_totals, raw_ungraded)
    return sorted(graded + ungraded, key=lambda item: item['start'])


def _build_course_group_homework_series(courses):
    """
    Build course_group-level homework_series by merging per-course series and averaging
    cumulative_grade across courses at each graded point. Parallels
    _get_grade_points_for_course_group() logic.

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
    grade_points = [(points[1] / 100) for points in _get_grade_points_for_course_group(course_group_id) if points]
    overall_grade = grade_points[-1] * 100 if len(grade_points) > 0 else -1
    trend = commonutils.calculate_trend(range(len(grade_points)), grade_points)

    logger.debug(f'Course Group {course_group_id} overall grade recalculated to '
                 f'{overall_grade} with {len(grade_points)} homework '
                 f'in {num_courses} courses')
    logger.debug(f'Course Group {course_group_id} trend recalculated to {trend}')

    # Update the values in the datastore, circumventing signals
    CourseGroup.objects.filter(pk=course_group_id).update(overall_grade=overall_grade, trend=trend)


def recalculate_course_grade(course_id):
    grade_points = [(points[1] / 100) for points in _get_grade_points_for_course(course_id) if points]
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

    weighted_graded_category_ids = [cid for cid, t in category_totals.items() if t['weight']]
    if whens:
        Category.objects.filter(
            pk__in=weighted_graded_category_ids
        ).update(grade_by_weight=Case(*whens, output_field=FloatField()))

    Category.objects.for_course(course_id).exclude(pk__in=weighted_graded_category_ids).update(grade_by_weight=0)


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
