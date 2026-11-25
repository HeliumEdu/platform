from django.test import TestCase

from helium.auth.models import UserOAuthProvider
from helium.common.errormessages import not_found_message
from helium.feed.models import ExternalCalendar
from helium.planner.models import Course, CourseGroup, Event, Homework, Resource, ResourceGroup


class TestCaseErrorMessages(TestCase):
    def test_not_found_message_names_the_item_as_the_app_does(self):
        for model, message in ((Course, 'Class not found.'),
                               (CourseGroup, 'Group not found.'),
                               (ResourceGroup, 'Group not found.'),
                               (Resource, 'Resource not found.'),
                               (Homework, 'Item not found.'),
                               (Event, 'Item not found.'),
                               (ExternalCalendar, 'Item not found.'),
                               (UserOAuthProvider, 'Item not found.')):
            with self.subTest(model=model):
                # WHEN
                result = not_found_message(model)

                # THEN
                self.assertEqual(result, message)
