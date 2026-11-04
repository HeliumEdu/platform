from django.db import IntegrityError, transaction
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup
from helium.planner.tests.helpers import attachmenthelper, coursegrouphelper, coursehelper, resourcegrouphelper, \
    resourcehelper


class TestCaseAttachment(TestCase):
    def tearDown(self):
        attachmenthelper.cleanup_attachments()

    def test_resource_attachment_belongs_to_the_resource_owner(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        attachment = attachmenthelper.given_attachment_exists(user, resource=resource)

        # THEN
        self.assertEqual(attachment.get_user(), user)

    def test_attachment_with_a_course_and_a_resource_violates_the_one_parent_constraint(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        resource = resourcehelper.given_resource_exists(resourcegrouphelper.given_resource_group_exists(user))

        # WHEN / THEN
        with self.assertRaises(IntegrityError), transaction.atomic():
            attachmenthelper.given_attachment_exists(user, course=course, resource=resource)

    def test_resource_and_resource_group_count_their_attachments(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource1 = resourcehelper.given_resource_exists(resource_group)
        resource2 = resourcehelper.given_resource_exists(resource_group)
        attachmenthelper.given_attachment_exists(user, resource=resource1)
        attachmenthelper.given_attachment_exists(user, resource=resource1)
        attachmenthelper.given_attachment_exists(user, resource=resource2)

        # WHEN
        resource1_count = resource1.num_attachments
        resource_group_count = resource_group.num_attachments

        # THEN
        self.assertEqual(resource1_count, 2)
        self.assertEqual(resource_group_count, 3)

    def test_course_groups_count_their_courses_attachments(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        attachmenthelper.given_attachment_exists(user, course=course)
        attachmenthelper.given_attachment_exists(user, course=course)

        # WHEN
        count = CourseGroup.objects.for_user(user.pk).num_attachments()

        # THEN
        self.assertEqual(count, 2)
