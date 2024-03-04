__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import datetime

from dateutil import parser

from helium.planner.models import CourseGroup


def given_course_group_exists(user, title='Test Course Group', start_date=datetime.date(2017, 1, 6),
                              end_date=datetime.date(2017, 5, 8),
                              shown_on_calendar=True):
    course_group = CourseGroup.objects.create(title=title,
                                              start_date=start_date,
                                              end_date=end_date,
                                              shown_on_calendar=shown_on_calendar,
                                              user=user)

    return course_group


def verify_course_group_matches_data(test_case, course_group, data):
    test_case.assertEqual(course_group.title, data['title'])
    test_case.assertEqual(course_group.start_date, parser.parse(data['start_date']).date())
    test_case.assertEqual(course_group.end_date, parser.parse(data['end_date']).date())
    test_case.assertEqual(course_group.shown_on_calendar, data['shown_on_calendar'])
    test_case.assertEqual(course_group.get_user().pk, data['user'])
