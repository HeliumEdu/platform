import logging

from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper, eventhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class TestCaseFeedViews(TestCase):
    def test_events_feed(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event1 = eventhelper.given_event_exists(user)
        event2 = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(reverse('feed_events_ical', kwargs={'slug': user.settings.private_slug}))

        # THEN
        print(response.content)
        # TODO: implement assertions

    def test_homework_feed(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group1 = coursegrouphelper.given_course_group_exists(user)
        course_group2 = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        category1 = categoryhelper.given_category_exists(course1, weight=50)
        category2 = categoryhelper.given_category_exists(course1, title='Test Category 2', weight=50)
        # This category having no weight will result in the course not having weighted grading
        category3 = categoryhelper.given_category_exists(course2, title='Test Category 3', weight=0)
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='20/30')
        homework2 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='25/30')
        homework3 = homeworkhelper.given_homework_exists(course1, category=category2, completed=True,
                                                         current_grade='15/30')
        homework4 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='20/30')
        homework5 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='25/30')
        # Incomplete homework are not graded
        homeworkhelper.given_homework_exists(course1, category=category2, current_grade='-1/100')
        # Completed homework with no grade set are not graded
        homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                             current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('feed_homework_ical', kwargs={'slug': user.settings.private_slug}))

        # THEN
        print(response.content)
        # TODO: implement assertions
