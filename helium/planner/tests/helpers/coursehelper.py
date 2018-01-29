import datetime

from dateutil import parser

from helium.planner.models import Course

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


def given_course_exists(course_group, title='Test Course', room='DNC 201', credits=5, color='#4986e7',
                        website='http://mycourse.com', is_online=False, teacher_name='My Teacher',
                        teacher_email='teacher@email.com', start_date=datetime.date(2017, 1, 6),
                        end_date=datetime.date(2017, 5, 8)):
    course = Course.objects.create(title=title,
                                   room=room,
                                   credits=credits,
                                   color=color,
                                   website=website,
                                   is_online=is_online,
                                   teacher_name=teacher_name,
                                   teacher_email=teacher_email,
                                   start_date=start_date,
                                   end_date=end_date,
                                   course_group=course_group)

    return course


def verify_course_matches_data(test_case, course, data):
    test_case.assertEqual(course.title, data['title'])
    test_case.assertEqual(course.room, data['room'])
    test_case.assertEqual(course.credits, float(data['credits']))
    test_case.assertEqual(course.color, data['color'])
    test_case.assertEqual(course.website, data['website'])
    test_case.assertEqual(course.is_online, data['is_online'])
    test_case.assertEqual(course.current_grade, float(data['current_grade']))
    test_case.assertEqual(course.trend, data['trend'])
    test_case.assertEqual(course.private_slug, data['private_slug'])
    test_case.assertEqual(course.teacher_name, data['teacher_name'])
    test_case.assertEqual(course.teacher_email, data['teacher_email'])
    test_case.assertEqual(course.start_date, parser.parse(data['start_date']).date())
    test_case.assertEqual(course.end_date, parser.parse(data['end_date']).date())
    test_case.assertEqual(course.days_of_week, data['days_of_week'])
    test_case.assertEqual(course.sun_start_time, parser.parse(data['sun_start_time']).time())
    test_case.assertEqual(course.sun_end_time, parser.parse(data['sun_end_time']).time())
    test_case.assertEqual(course.mon_start_time, parser.parse(data['mon_start_time']).time())
    test_case.assertEqual(course.mon_end_time, parser.parse(data['mon_end_time']).time())
    test_case.assertEqual(course.tue_start_time, parser.parse(data['tue_start_time']).time())
    test_case.assertEqual(course.tue_end_time, parser.parse(data['tue_end_time']).time())
    test_case.assertEqual(course.wed_start_time, parser.parse(data['wed_start_time']).time())
    test_case.assertEqual(course.wed_end_time, parser.parse(data['wed_end_time']).time())
    test_case.assertEqual(course.thu_start_time, parser.parse(data['thu_start_time']).time())
    test_case.assertEqual(course.thu_end_time, parser.parse(data['thu_end_time']).time())
    test_case.assertEqual(course.fri_start_time, parser.parse(data['fri_start_time']).time())
    test_case.assertEqual(course.fri_end_time, parser.parse(data['fri_end_time']).time())
    test_case.assertEqual(course.sat_start_time, parser.parse(data['sat_start_time']).time())
    test_case.assertEqual(course.sat_end_time, parser.parse(data['sat_end_time']).time())
    test_case.assertEqual(course.days_of_week_alt, data['days_of_week_alt'])
    test_case.assertEqual(course.sun_start_time_alt, parser.parse(data['sun_start_time_alt']).time())
    test_case.assertEqual(course.sun_end_time_alt, parser.parse(data['sun_end_time_alt']).time())
    test_case.assertEqual(course.mon_start_time_alt, parser.parse(data['mon_start_time_alt']).time())
    test_case.assertEqual(course.mon_end_time_alt, parser.parse(data['mon_end_time_alt']).time())
    test_case.assertEqual(course.tue_start_time_alt, parser.parse(data['tue_start_time_alt']).time())
    test_case.assertEqual(course.tue_end_time_alt, parser.parse(data['tue_end_time_alt']).time())
    test_case.assertEqual(course.wed_start_time_alt, parser.parse(data['wed_start_time_alt']).time())
    test_case.assertEqual(course.wed_end_time_alt, parser.parse(data['wed_end_time_alt']).time())
    test_case.assertEqual(course.thu_start_time_alt, parser.parse(data['thu_start_time_alt']).time())
    test_case.assertEqual(course.thu_end_time_alt, parser.parse(data['thu_end_time_alt']).time())
    test_case.assertEqual(course.fri_start_time_alt, parser.parse(data['fri_start_time_alt']).time())
    test_case.assertEqual(course.fri_end_time_alt, parser.parse(data['fri_end_time_alt']).time())
    test_case.assertEqual(course.sat_start_time_alt, parser.parse(data['sat_start_time_alt']).time())
    test_case.assertEqual(course.sat_end_time_alt, parser.parse(data['sat_end_time_alt']).time())
    test_case.assertEqual(course.course_group.pk, int(data['course_group']))
