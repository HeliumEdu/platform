import datetime

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.services import recurrenceservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper


class TestCaseRecurrenceService(TestCase):
    def test_bound_to_course_keeps_a_rule_that_already_ends(self):
        # GIVEN
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        start = datetime.datetime(2017, 4, 3, 16, 0, tzinfo=datetime.timezone.utc)

        for rule in ('FREQ=WEEKLY;BYDAY=MO;COUNT=10', 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20170710T235959Z'):
            with self.subTest(rule=rule):
                # WHEN
                bounded = recurrenceservice.bound_to_course(rule, start, start + datetime.timedelta(hours=1), False,
                                                            course)

                # THEN
                self.assertEqual(bounded, rule)
