import logging

import icalendar
from django.urls import reverse

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    homeworkhelper, eventhelper

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.4.10'

logger = logging.getLogger(__name__)


class TestCasePrivateViews(CacheTestCase):
    def test_events_feed(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user1.settings.enable_private_slug()
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        user2.settings.enable_private_slug()
        event1 = eventhelper.given_event_exists(user1)
        event2 = eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)

        # WHEN
        response = self.client.get(reverse("feed_private_events_ical", kwargs={"slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 2)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], event1.title)
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'], "Comments: {}".format(event1.comments))
        self.assertEqual(calendar.subcomponents[0]['DTSTART'].dt, event1.start)
        self.assertEqual(calendar.subcomponents[0]['DTEND'].dt, event1.end)
        self.assertEqual(calendar.subcomponents[1]['SUMMARY'], event1.title)
        self.assertEqual(calendar.subcomponents[1]['DTSTART'].dt, event2.start)
        self.assertEqual(calendar.subcomponents[1]['DTEND'].dt, event2.end)
        self.assertEqual(calendar.subcomponents[1]['DESCRIPTION'], "Comments: {}".format(event2.comments))

    def test_homework_feed(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user1.settings.enable_private_slug()
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        user2.settings.enable_private_slug()
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user1)
        course_group3 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1, room='')
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group3)
        category1 = categoryhelper.given_category_exists(course1, title='Uncategorized')
        category2 = categoryhelper.given_category_exists(course2)
        category3 = categoryhelper.given_category_exists(course3)
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade="20/30")
        homework2 = homeworkhelper.given_homework_exists(course2, category=category2, current_grade="-1/100")
        homeworkhelper.given_homework_exists(course3, category=category3, completed=True, current_grade="-1/100")

        # WHEN
        response = self.client.get(reverse("feed_private_homework_ical", kwargs={"slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 2)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], homework1.title)
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         'Class Info: {}\nGrade: {}\nComments: {}'.format(homework1.course.title,
                                                                          homework1.current_grade,
                                                                          homework1.comments))
        self.assertEqual(calendar.subcomponents[0]['DTSTART'].dt, homework1.start)
        self.assertEqual(calendar.subcomponents[0]['DTEND'].dt, homework1.end)
        self.assertEqual(calendar.subcomponents[1]['SUMMARY'], homework2.title)
        self.assertEqual(calendar.subcomponents[1]['DTSTART'].dt, homework2.start)
        self.assertEqual(calendar.subcomponents[1]['DTEND'].dt, homework2.end)
        self.assertEqual(calendar.subcomponents[1]['DESCRIPTION'],
                         'Class Info: {} for {} in {}\nComments: {}'.format(homework2.category.title,
                                                                            homework2.course.title,
                                                                            homework2.course.room,
                                                                            homework2.comments))

    def test_courseschedules_feed(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user1.settings.enable_private_slug()
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        user2.settings.enable_private_slug()
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user1)
        course_group3 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1, room='SSC 123')
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group3)
        courseschedulehelper.given_course_schedule_exists(course1)
        courseschedulehelper.given_course_schedule_exists(course2)
        courseschedulehelper.given_course_schedule_exists(course3)

        # WHEN
        response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 106)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], course1.title)
        self.assertEqual(str(calendar.subcomponents[0]['DTSTART'].dt), '2017-01-06 02:30:00-08:00')
        self.assertEqual(str(calendar.subcomponents[0]['DTEND'].dt), '2017-01-06 05:00:00-08:00')
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         'Comments: <a href="{}">{}</a> in {}'.format(course1.website, course1.title, course1.room))
