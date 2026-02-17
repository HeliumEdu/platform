__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.auth.utils.userutils import generate_unique_username_from_email


class TestCaseUserUtils(TestCase):
    def test_generate_unique_username_from_email_uses_local_part(self):
        username = generate_unique_username_from_email('Student.Name+1@example.com')
        self.assertEqual(username, 'student.name+1')

    def test_generate_unique_username_from_email_appends_counter_on_collision(self):
        userhelper.given_a_user_exists(username='student', email='existing@example.com')
        username = generate_unique_username_from_email('student@example.com')
        self.assertEqual(username, 'student1')
