"""
Helper for CourseGroup models in testing.
"""
import datetime

from helium.planner.models import CourseGroup

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_course_group_exists(user, title='Test Course Group', start_date=datetime.date(2014, 1, 6), end_date=datetime.date(2014, 5, 8),
                              shown_on_calendar=True):
    course_group = CourseGroup.objects.create(title=title,
                                              start_date=start_date,
                                              end_date=end_date,
                                              shown_on_calendar=shown_on_calendar,
                                              user=user)

    return course_group
