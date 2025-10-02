__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import datetime

from dateutil import parser

from helium.planner.models import CourseSchedule


def given_course_schedule_exists(course, days_of_week='0101010',
                                 sun_start_time=datetime.time(12, 0, 0), sun_end_time=datetime.time(12, 0, 0),
                                 mon_start_time=datetime.time(2, 30, 0), mon_end_time=datetime.time(3, 0, 0),
                                 tue_start_time=datetime.time(12, 0, 0), tue_end_time=datetime.time(12, 0, 0),
                                 wed_start_time=datetime.time(2, 30, 0), wed_end_time=datetime.time(3, 0, 0),
                                 thu_start_time=datetime.time(12, 0, 0), thu_end_time=datetime.time(12, 0, 0),
                                 fri_start_time=datetime.time(2, 30, 0), fri_end_time=datetime.time(5, 0, 0),
                                 sat_start_time=datetime.time(12, 0, 0), sat_end_time=datetime.time(12, 0, 0)):
    course_schedule = CourseSchedule.objects.create(days_of_week=days_of_week,
                                                    sun_start_time=sun_start_time, sun_end_time=sun_end_time,
                                                    mon_start_time=mon_start_time, mon_end_time=mon_end_time,
                                                    tue_start_time=tue_start_time, tue_end_time=tue_end_time,
                                                    wed_start_time=wed_start_time, wed_end_time=wed_end_time,
                                                    thu_start_time=thu_start_time, thu_end_time=thu_end_time,
                                                    fri_start_time=fri_start_time, fri_end_time=fri_end_time,
                                                    sat_start_time=sat_start_time, sat_end_time=sat_end_time,
                                                    course=course)

    return course_schedule


def verify_course_schedule_matches(test_case, schedule, data):
    test_case.assertEqual(schedule.days_of_week, data['days_of_week'])
    test_case.assertEqual(schedule.sun_start_time, parser.parse(data['sun_start_time']).time())
    test_case.assertEqual(schedule.sun_end_time, parser.parse(data['sun_end_time']).time())
    test_case.assertEqual(schedule.mon_start_time, parser.parse(data['mon_start_time']).time())
    test_case.assertEqual(schedule.mon_end_time, parser.parse(data['mon_end_time']).time())
    test_case.assertEqual(schedule.tue_start_time, parser.parse(data['tue_start_time']).time())
    test_case.assertEqual(schedule.tue_end_time, parser.parse(data['tue_end_time']).time())
    test_case.assertEqual(schedule.wed_start_time, parser.parse(data['wed_start_time']).time())
    test_case.assertEqual(schedule.wed_end_time, parser.parse(data['wed_end_time']).time())
    test_case.assertEqual(schedule.thu_start_time, parser.parse(data['thu_start_time']).time())
    test_case.assertEqual(schedule.thu_end_time, parser.parse(data['thu_end_time']).time())
    test_case.assertEqual(schedule.fri_start_time, parser.parse(data['fri_start_time']).time())
    test_case.assertEqual(schedule.fri_end_time, parser.parse(data['fri_end_time']).time())
    test_case.assertEqual(schedule.sat_start_time, parser.parse(data['sat_start_time']).time())
    test_case.assertEqual(schedule.sat_end_time, parser.parse(data['sat_end_time']).time())
    if 'course' in data:
        test_case.assertEqual(schedule.course.pk, int(data['course']))
