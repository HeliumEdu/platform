__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import time

import icalendar
from django.urls import reverse
from django.utils.http import http_date

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    homeworkhelper, eventhelper

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
        response = self.client.get(reverse("feed_private_events_ical", kwargs={"private_slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 2)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], event1.title)
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'], f"Comments: {event1.comments}")
        self.assertEqual(calendar.subcomponents[0]['DTSTART'].dt, event1.start)
        self.assertEqual(calendar.subcomponents[0]['DTEND'].dt, event1.end)
        self.assertEqual(calendar.subcomponents[1]['SUMMARY'], event1.title)
        self.assertEqual(calendar.subcomponents[1]['DTSTART'].dt, event2.start)
        self.assertEqual(calendar.subcomponents[1]['DTEND'].dt, event2.end)
        self.assertEqual(calendar.subcomponents[1]['DESCRIPTION'], f"Comments: {event2.comments}")

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
        response = self.client.get(reverse("feed_private_homework_ical", kwargs={"private_slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 2)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], homework1.title)
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         f'Class Info: {homework1.course.title}\nGrade: {homework1.current_grade}\nComments: {homework1.comments}')
        self.assertEqual(calendar.subcomponents[0]['DTSTART'].dt, homework1.start)
        self.assertEqual(calendar.subcomponents[0]['DTEND'].dt, homework1.end)
        self.assertEqual(calendar.subcomponents[1]['SUMMARY'], homework2.title)
        self.assertEqual(calendar.subcomponents[1]['DTSTART'].dt, homework2.start)
        self.assertEqual(calendar.subcomponents[1]['DTEND'].dt, homework2.end)
        self.assertEqual(calendar.subcomponents[1]['DESCRIPTION'],
                         f'Class Info: {homework2.category.title} for {homework2.course.title} in {homework2.course.room}\nComments: {homework2.comments}')

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
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 106)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], course1.title)
        self.assertEqual(str(calendar.subcomponents[0]['DTSTART'].dt), '2017-01-06 02:30:00-08:00')
        self.assertEqual(str(calendar.subcomponents[0]['DTEND'].dt), '2017-01-06 05:00:00-08:00')
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         f'URL: {course1.website}\nComments: <a href="{course1.website}">{course1.title}</a> in {course1.room}')

    # Events feed conditional request tests

    def test_events_feed_returns_etag_and_last_modified_headers(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIn('Last-Modified', response)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], 'private, max-age=0, must-revalidate')
        self.assertIn(str(user.pk), response['ETag'])

    def test_events_feed_returns_etag_without_last_modified_when_empty(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()

        # WHEN
        response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertEqual(response['ETag'], f'"{user.pk}:0"')
        self.assertNotIn('Last-Modified', response)

    def test_events_feed_returns_304_on_matching_etag(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(user)

        # Get initial response to obtain ETag
        initial_response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # WHEN
        response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 304)
        self.assertEqual(response['ETag'], etag)
        self.assertEqual(len(response.content), 0)

    def test_events_feed_returns_304_on_if_modified_since(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(user)

        # Get initial response to obtain Last-Modified
        initial_response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}))
        last_modified = initial_response['Last-Modified']

        # WHEN
        response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_MODIFIED_SINCE=last_modified)

        # THEN
        self.assertEqual(response.status_code, 304)

    def test_events_feed_returns_200_after_data_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)

        initial_response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # Sleep to ensure timestamp changes
        time.sleep(1.1)

        # Modify event to change updated_at
        event.title = 'Updated Title'
        event.save()

        # WHEN
        response = self.client.get(
            reverse("feed_private_events_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)

    # Homework feed conditional request tests

    def test_homework_feed_returns_etag_and_last_modified_headers(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIn('Last-Modified', response)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], 'private, max-age=0, must-revalidate')

    def test_homework_feed_returns_304_on_matching_etag(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        initial_response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # WHEN
        response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 304)

    def test_homework_feed_returns_304_on_if_modified_since(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        initial_response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}))
        last_modified = initial_response['Last-Modified']

        # WHEN
        response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_MODIFIED_SINCE=last_modified)

        # THEN
        self.assertEqual(response.status_code, 304)

    def test_homework_feed_returns_200_after_data_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        initial_response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # Sleep to ensure timestamp changes
        time.sleep(1.1)

        # Modify homework to change updated_at
        homework.title = 'Updated Homework'
        homework.save()

        # WHEN
        response = self.client.get(
            reverse("feed_private_homework_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)

    # Course schedules feed conditional request tests

    def test_courseschedules_feed_returns_etag_and_last_modified_headers(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIn('Last-Modified', response)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], 'private, max-age=0, must-revalidate')

    def test_courseschedules_feed_returns_304_on_matching_etag(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        initial_response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # WHEN
        response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 304)

    def test_courseschedules_feed_returns_304_on_if_modified_since(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        initial_response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}))
        last_modified = initial_response['Last-Modified']

        # WHEN
        response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_MODIFIED_SINCE=last_modified)

        # THEN
        self.assertEqual(response.status_code, 304)

    def test_courseschedules_feed_returns_200_after_data_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        initial_response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # Sleep to ensure timestamp changes
        time.sleep(1.1)

        # Modify course to change updated_at
        course.title = 'Updated Course'
        course.save()

        # WHEN
        response = self.client.get(
            reverse("feed_private_courseschedules_ical", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)
