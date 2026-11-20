# The score a class needs on its remaining work to reach a desired overall grade or term GPA, with work not yet graded
# taken at the class's current pace. It works on the aggregates gradingservice.get_grade_data() builds.

import logging
from decimal import Decimal

from rest_framework.exceptions import NotFound, ValidationError

from helium.planner.services import gradingservice

logger = logging.getLogger(__name__)

ACHIEVABLE = 'achievable'
ABOVE_TARGET = 'above_target'
UNACHIEVABLE = 'unachievable'
TARGET_CATEGORY_HAS_NO_WEIGHT = 'target_category_has_no_weight'
GPA_UNREACHABLE = 'gpa_unreachable'


def calculate_needed_grade(categories, target_category_id, desired_overall_grade, current_grade):
    """
    The average a weighted class needs in one category to reach a desired overall grade:
    (desired * total weight - sum of the other categories' weight * grade) / the target category's weight. Each other
    category with assignments counts at its average, or at the class's current grade while it has nothing graded (left
    out while the class has no grade either), so the rest of the class keeps its current pace. The target's own
    current average is ignored.

    :param categories: The class's categories, each with `id`, `weight`, `num_homework`, and `overall_grade` (`-1`
        when nothing is graded).
    :param target_category_id: The category to solve for.
    :param desired_overall_grade: The desired overall grade (0-100).
    :param current_grade: The class's current grade (0-100), or `-1` when nothing is graded.
    :return: A dict with `needed_grade` and `state`.
    """
    target_category = next((category for category in categories if category['id'] == target_category_id), None)
    if target_category is None:
        raise ValueError('Category not found')

    target_weight = float(target_category['weight'])
    if target_weight <= 0:
        return {'needed_grade': 0, 'state': TARGET_CATEGORY_HAS_NO_WEIGHT}

    sum_of_other_weighted_grades = 0
    total_weight = target_weight

    for category in categories:
        weight = float(category['weight'])
        if category['id'] == target_category_id or weight <= 0 or category['num_homework'] == 0:
            continue

        grade = float(category['overall_grade'])
        if grade < 0:
            grade = float(current_grade)
        if grade < 0:
            continue

        sum_of_other_weighted_grades += weight * grade
        total_weight += weight

    needed_grade = (desired_overall_grade * total_weight - sum_of_other_weighted_grades) / target_weight

    return {'needed_grade': needed_grade, 'state': _state_for(needed_grade)}


def calculate_needed_assignment_score(graded_points_earned, graded_points_possible, assignment_points_possible,
                                      desired_overall_grade, other_remaining_points_possible=0):
    """
    The score needed on one remaining assignment, as a percentage of its points possible, to bring a points-based
    total (earned over possible) to a desired grade. The other remaining assignments come in at the graded work's
    average, the class's current pace (left out while nothing is graded).

    :param graded_points_earned: Points earned on graded work.
    :param graded_points_possible: Points possible on graded work.
    :param assignment_points_possible: The remaining assignment's points possible.
    :param desired_overall_grade: The desired grade (0-100).
    :param other_remaining_points_possible: Points possible on the other assignments still to be graded.
    :return: A dict with `needed_grade` and `state`.
    """
    if graded_points_possible > 0:
        other_points_possible = other_remaining_points_possible
        other_points_earned = graded_points_earned / graded_points_possible * other_remaining_points_possible
    else:
        other_points_possible = other_points_earned = 0
    needed_points = (desired_overall_grade / 100
                     * (graded_points_possible + other_points_possible + assignment_points_possible)
                     - graded_points_earned - other_points_earned)
    needed_grade = needed_points / assignment_points_possible * 100

    return {'needed_grade': needed_grade, 'state': _state_for(needed_grade)}


def to_assignment_score(category_need, category_graded_points_earned, category_graded_points_possible,
                        assignment_points_possible):
    """
    Convert a needed category average into the score needed on that category's one remaining assignment, from the
    category's graded points. A target category with no weight passes through unchanged.

    :param category_need: The result of `calculate_needed_grade()`.
    :param category_graded_points_earned: The category's points earned on graded work.
    :param category_graded_points_possible: The category's points possible on graded work.
    :param assignment_points_possible: The remaining assignment's points possible.
    :return: A dict with `needed_grade` and `state`.
    """
    if category_need['state'] == TARGET_CATEGORY_HAS_NO_WEIGHT:
        return category_need

    return calculate_needed_assignment_score(category_graded_points_earned, category_graded_points_possible,
                                             assignment_points_possible, category_need['needed_grade'])


def get_needed_grade(user_id, course_id, target_id, desired_grade=None, desired_gpa=None) -> dict:
    """
    What a class needs to reach a desired overall grade, or a desired term GPA.

    A weighted class (any category with weight) solves for a category with weight and exactly one ungraded assignment
    left, then for that assignment's score when it's in the class's ungraded work. A points-based class solves for one
    of its ungraded assignments. Either way, the rest of the class's ungraded work is taken at its current pace. A
    desired term GPA is first turned into the lowest band of the class's grade scale that brings the term GPA to it,
    with the GPA rounded to two places, and that band's `min_grade` is solved for.

    :param user_id: The user whose class it is.
    :param course_id: The class.
    :param target_id: A category (weighted class) or an ungraded assignment (points-based class).
    :param desired_grade: The desired overall grade (0-100), or None when `desired_gpa` is given.
    :param desired_gpa: The desired term GPA, or None when `desired_grade` is given.
    :return: A dict with `state`, `needed_grade`, `weighted`, `category` (weighted classes), `assignment` (when one is
        solved for, with `needed_points`), and `grade_band` (for a desired GPA: the band solved for, or the class's top
        band when even it falls short).
    """
    if desired_grade is None and desired_gpa is None:
        raise ValidationError("One of 'desired_grade' or 'desired_gpa' must be given.")
    if desired_grade is not None and desired_gpa is not None:
        raise ValidationError("Only one of 'desired_grade' or 'desired_gpa' may be given.")
    if desired_grade is not None and not 0 <= desired_grade <= 100:
        raise ValidationError({'desired_grade': 'Enter a valid grade between 0 and 100.'})
    if desired_gpa is not None and not 0 <= desired_gpa:
        raise ValidationError({'desired_gpa': 'Enter a valid GPA.'})

    course_group, course = next(((course_group, course)
                                 for course_group in gradingservice.get_grade_data(user_id)['course_groups']
                                 for course in course_group['courses'] if course['id'] == course_id),
                                (None, None))
    if course is None:
        raise NotFound('No Course matches the given query.')
    categories = course['categories']
    ungraded = [item for item in course['homework_series'] if not item.graded]
    weighted = any(float(category['weight']) > 0 for category in categories)

    if weighted:
        category = next((category for category in categories
                         if category['id'] == target_id and float(category['weight']) > 0
                         and category['num_homework'] - category['num_homework_graded'] == 1), None)
        if category is None:
            raise ValidationError({'target': 'Select a category that is down to its last ungraded assignment.'})
        remaining = [item for item in ungraded if item.category_id == target_id]
        assignment = remaining[0] if len(remaining) == 1 else None
    else:
        category = None
        assignment = next((item for item in ungraded if item.id == target_id), None)
        if assignment is None:
            raise ValidationError({'target': 'Select an ungraded assignment in this class.'})

    grade_band = None
    if desired_gpa is not None:
        grade_band, reaches = _grade_band_for_gpa(course_group, course, desired_gpa)
        if not reaches:
            return _describe({'state': GPA_UNREACHABLE, 'needed_grade': 0}, weighted, category, None, grade_band)
        desired_grade = grade_band['min_grade']

    if weighted:
        category_need = calculate_needed_grade(categories, target_id, desired_grade, float(course['overall_grade']))
        result = category_need if assignment is None else to_assignment_score(
            category_need, float(category['points_earned']), float(category['points_possible']),
            assignment.points_possible)
    else:
        other_remaining_points_possible = sum(float(item.points_possible or 0) for item in ungraded
                                              if item is not assignment)
        result = calculate_needed_assignment_score(float(course['points_earned']), float(course['points_possible']),
                                                   assignment.points_possible, desired_grade,
                                                   other_remaining_points_possible)

    return _describe(result, weighted, category, assignment, grade_band)


def _grade_band_for_gpa(course_group, course, desired_gpa):
    grade_scale = course['grade_scale']
    if not grade_scale:
        raise ValidationError({'desired_gpa': "Set a grade scale on the class's group to plan for a GPA."})
    credits = Decimal(str(course['credits']))
    if credits <= 0:
        raise ValidationError({'desired_gpa': 'Add credits to this class to plan for a GPA.'})

    other_classes = [(other['credits'], other['grade_point']) for other in course_group['courses']
                     if other['id'] != course['id']]
    desired = Decimal(str(desired_gpa))
    higher_is_better = grade_scale[-1]['grade_point'] >= grade_scale[0]['grade_point']
    for band in grade_scale:
        gpa = gradingservice.displayed_gpa(gradingservice.gpa_for(other_classes + [(credits, band['grade_point'])]))
        if (gpa >= desired) if higher_is_better else (gpa <= desired):
            return band, True

    return grade_scale[-1], False


def _state_for(needed_grade):
    if needed_grade < 0:
        return ABOVE_TARGET
    if needed_grade > 100:
        return UNACHIEVABLE
    return ACHIEVABLE


def _describe(result, weighted, category, assignment, grade_band=None):
    described = {
        'state': result['state'],
        'needed_grade': result['needed_grade'],
        'weighted': weighted,
        'category': {'id': category['id'], 'title': category['title']} if category else None,
        'assignment': None,
        'grade_band': grade_band,
    }
    if assignment is not None and result['state'] != TARGET_CATEGORY_HAS_NO_WEIGHT:
        described['assignment'] = {
            'id': assignment.id,
            'title': assignment.title,
            'points_possible': assignment.points_possible,
            'needed_points': result['needed_grade'] / 100 * assignment.points_possible,
        }
    return described
