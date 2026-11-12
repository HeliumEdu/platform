import datetime

from dateutil import parser

from helium.common import enums
from helium.common.utils import gradeutils
from helium.planner.models import CourseGroup


def given_course_group_exists(user, title='🍂 Test Course Group', start_date=datetime.date(2017, 1, 6),
                              end_date=datetime.date(2017, 5, 8),
                              shown_on_calendar=True, grade_scale_template=enums.GRADE_SCALE_4_0, grade_scale=None,
                              example_schedule=False):
    course_group = CourseGroup.objects.create(title=title,
                                              start_date=start_date,
                                              end_date=end_date,
                                              shown_on_calendar=shown_on_calendar,
                                              grade_scale=(gradeutils.preset_grade_scale(grade_scale_template)
                                                           if grade_scale is None else grade_scale),
                                              grade_scale_template=(grade_scale_template if grade_scale is None
                                                                    else gradeutils.preset_for(grade_scale)),
                                              example_schedule=example_schedule,
                                              user=user)

    return course_group


def verify_course_group_matches_data(test_case, course_group, data):
    test_case.assertEqual(course_group.title, data['title'])
    test_case.assertEqual(course_group.start_date, parser.parse(data['start_date']).date())
    test_case.assertEqual(course_group.end_date, parser.parse(data['end_date']).date())
    test_case.assertEqual(course_group.shown_on_calendar, data['shown_on_calendar'])
    if 'overall_grade' in data:
        test_case.assertEqual(float(course_group.overall_grade), float(data['overall_grade']))
    if 'trend' in data:
        test_case.assertEqual(course_group.trend, data['trend'])
    test_case.assertEqual(course_group.get_user().pk, data['user'])
