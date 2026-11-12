import datetime

from dateutil import parser

from helium.planner.models import Course
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, homeworkhelper


def given_course_exists(course_group, title='🧪 Test Course', room='DNC 201', credits=0, color='#4986e7',
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


def given_course_with_category_exists(user, course_group_kwargs=None, course_kwargs=None, category_kwargs=None):
    course_group = coursegrouphelper.given_course_group_exists(user, **(course_group_kwargs or {}))
    course = given_course_exists(course_group, **(course_kwargs or {}))
    category = categoryhelper.given_category_exists(course, **(category_kwargs or {}))

    return course_group, course, category


def given_graded_course_exists(course_group, grade, credits=0):
    course = given_course_exists(course_group, credits=credits)
    category = categoryhelper.given_category_exists(course)
    homeworkhelper.given_homework_exists(course, category=category, completed=True, current_grade=f'{grade}/100')

    return course


def given_weekly_homework_in_a_new_course_exists(user, **kwargs):
    course = given_course_exists(coursegrouphelper.given_course_group_exists(user))
    return homeworkhelper.given_weekly_homework_exists(course, **kwargs)


def verify_course_matches_data(test_case, course, data):
    test_case.assertEqual(course.title, data['title'])
    test_case.assertEqual(course.room, data['room'])
    test_case.assertEqual(course.credits, float(data['credits']))
    test_case.assertEqual(course.color, data['color'])
    test_case.assertEqual(course.website, data['website'])
    test_case.assertEqual(course.is_online, data['is_online'])
    test_case.assertEqual(float(course.current_grade), float(data['current_grade']))
    test_case.assertEqual(course.trend, data['trend'])
    test_case.assertEqual(course.teacher_name, data['teacher_name'])
    test_case.assertEqual(course.teacher_email, data['teacher_email'])
    test_case.assertEqual(course.start_date, parser.parse(data['start_date']).date())
    test_case.assertEqual(course.end_date, parser.parse(data['end_date']).date())
    test_case.assertEqual(course.course_group.pk, int(data['course_group']))
