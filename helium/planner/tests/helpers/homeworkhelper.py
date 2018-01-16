import datetime

from dateutil import parser
from django.utils import timezone

from helium.common import enums
from helium.planner.models import Homework

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_homework_exists(course, title='Test Homework', all_day=False, show_end_time=True,
                          start=datetime.datetime(2014, 5, 8, 16, 0, 0, tzinfo=timezone.utc),
                          end=datetime.datetime(2014, 5, 8, 18, 0, 0, tzinfo=timezone.utc),
                          priority=65, comments='A comment on a homework.', current_grade='25/30', completed=False,
                          category=None, materials=None):
    if materials is None:
        materials = []

    homework = Homework.objects.create(title=title,
                                       all_day=all_day,
                                       show_end_time=show_end_time,
                                       start=start,
                                       end=end,
                                       priority=priority,
                                       comments=comments,
                                       current_grade=current_grade,
                                       completed=completed,
                                       category=category,
                                       course=course)

    for material in materials:
        homework.materials.add(material)

    return homework


def verify_homework_matches_data(test_case, homework, data):
    test_case.assertEqual(homework.title, data['title'])
    test_case.assertEqual(homework.all_day, data['all_day'])
    test_case.assertEqual(homework.show_end_time, data['show_end_time'])
    test_case.assertEqual(homework.start, parser.parse(data['start']))
    test_case.assertEqual(homework.end, parser.parse(data['end']))
    test_case.assertEqual(homework.priority, data['priority'])
    test_case.assertEqual(homework.comments, data['comments'])
    test_case.assertEqual(homework.current_grade, data['current_grade'])
    test_case.assertEqual(homework.completed, data['completed'])
    if 'category' in data:
        test_case.assertEqual(homework.category.pk, int(data['category']))
    for material_id in data['materials']:
        test_case.assertTrue(homework.materials.filter(pk=material_id).exists())
    test_case.assertEqual(homework.course.pk, int(data['course']))
