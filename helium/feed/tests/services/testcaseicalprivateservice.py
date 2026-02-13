__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import datetime
from unittest import mock

from django.test import TestCase, RequestFactory
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.feed.services import icalprivateservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    homeworkhelper, eventhelper

logger = logging.getLogger(__name__)


class TestCaseGetEventsLastModified(TestCase):
    def test_returns_max_timestamp(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event1 = eventhelper.given_event_exists(user)
        event2 = eventhelper.given_event_exists(user)
        # Make event2 have a later updated_at
        event2.title = 'Updated'
        event2.save()

        # WHEN
        result = icalprivateservice.get_events_last_modified(user)

        # THEN
        self.assertIsNotNone(result)
        self.assertEqual(result, event2.updated_at)

    def test_returns_none_for_empty(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        result = icalprivateservice.get_events_last_modified(user)

        # THEN
        self.assertIsNone(result)


class TestCaseGetHomeworkLastModified(TestCase):
    def test_returns_max_timestamp_from_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        # Make homework have the latest timestamp
        homework.title = 'Updated Homework'
        homework.save()

        # WHEN
        result = icalprivateservice.get_homework_last_modified(user)

        # THEN
        self.assertIsNotNone(result)
        # Result should be the max across homework, course, category
        self.assertGreaterEqual(result, homework.updated_at)

    def test_returns_max_timestamp_from_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)
        # Make course have the latest timestamp
        course.title = 'Updated Course'
        course.save()

        # WHEN
        result = icalprivateservice.get_homework_last_modified(user)

        # THEN
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, course.updated_at)

    def test_returns_none_for_empty(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        result = icalprivateservice.get_homework_last_modified(user)

        # THEN
        self.assertIsNone(result)


class TestCaseGetCourseschedulesLastModified(TestCase):
    def test_returns_max_timestamp(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule = courseschedulehelper.given_course_schedule_exists(course)
        # Update to get a newer timestamp
        schedule.days_of_week = '1111111'
        schedule.save()

        # WHEN
        result = icalprivateservice.get_courseschedules_last_modified(user)

        # THEN
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, schedule.updated_at)

    def test_returns_none_for_empty(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        result = icalprivateservice.get_courseschedules_last_modified(user)

        # THEN
        self.assertIsNone(result)


class TestCaseGenerateEtag(TestCase):
    def test_format_with_timestamp(self):
        # GIVEN
        user_id = 123
        last_modified = timezone.now()

        # WHEN
        result = icalprivateservice.generate_etag(user_id, last_modified)

        # THEN
        self.assertTrue(result.startswith('"'))
        self.assertTrue(result.endswith('"'))
        self.assertIn('123:', result)
        self.assertNotIn(':0"', result)

    def test_format_without_timestamp(self):
        # GIVEN
        user_id = 456

        # WHEN
        result = icalprivateservice.generate_etag(user_id, None)

        # THEN
        self.assertEqual(result, '"456:0"')


class TestCaseCheckConditionalRequest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_304_on_etag_match(self):
        # GIVEN
        request = self.factory.get('/', HTTP_IF_NONE_MATCH='"123:1234567890"')
        etag = '"123:1234567890"'
        last_modified = timezone.now()

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 304)
        self.assertEqual(result['ETag'], etag)

    def test_returns_304_on_wildcard_etag(self):
        # GIVEN
        request = self.factory.get('/', HTTP_IF_NONE_MATCH='*')
        etag = '"123:1234567890"'
        last_modified = timezone.now()

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 304)

    def test_returns_none_on_etag_mismatch(self):
        # GIVEN
        request = self.factory.get('/', HTTP_IF_NONE_MATCH='"123:9999999999"')
        etag = '"123:1234567890"'
        last_modified = timezone.now()

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        self.assertIsNone(result)

    def test_returns_304_on_if_modified_since_match(self):
        # GIVEN
        last_modified = timezone.now()
        # Create a request with If-Modified-Since in the future
        http_date_str = 'Wed, 01 Jan 2099 00:00:00 GMT'
        request = self.factory.get('/', HTTP_IF_MODIFIED_SINCE=http_date_str)
        etag = '"123:1234567890"'

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 304)

    def test_returns_none_on_if_modified_since_stale(self):
        # GIVEN
        last_modified = timezone.now()
        # Create a request with If-Modified-Since in the past
        http_date_str = 'Wed, 01 Jan 2000 00:00:00 GMT'
        request = self.factory.get('/', HTTP_IF_MODIFIED_SINCE=http_date_str)
        etag = '"123:1234567890"'

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        self.assertIsNone(result)

    def test_returns_none_when_no_conditional_headers(self):
        # GIVEN
        request = self.factory.get('/')
        etag = '"123:1234567890"'
        last_modified = timezone.now()

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        self.assertIsNone(result)

    def test_handles_none_last_modified_with_if_modified_since(self):
        # GIVEN
        request = self.factory.get('/', HTTP_IF_MODIFIED_SINCE='Wed, 01 Jan 2099 00:00:00 GMT')
        etag = '"123:0"'
        last_modified = None

        # WHEN
        result = icalprivateservice.check_conditional_request(request, etag, last_modified)

        # THEN
        # Should return None since there's no last_modified to compare
        self.assertIsNone(result)
