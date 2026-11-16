import datetime
import logging
import time

import icalendar
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    homeworkhelper, eventhelper, notehelper, resourcegrouphelper, resourcehelper

logger = logging.getLogger(__name__)

class TestCaseFeedViews(TestCase):
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
        response = self.client.get(reverse("feed_events", kwargs={"private_slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 2)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], event1.title)
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         f'\U0001F517 Open in Helium: {settings.PROJECT_APP_HOST}/planner/event/{event1.pk}/details')
        self.assertEqual(calendar.subcomponents[0]['DTSTART'].dt, event1.start)
        self.assertEqual(calendar.subcomponents[0]['DTEND'].dt, event1.end)
        self.assertEqual(calendar.subcomponents[1]['SUMMARY'], event1.title)
        self.assertEqual(calendar.subcomponents[1]['DTSTART'].dt, event2.start)
        self.assertEqual(calendar.subcomponents[1]['DTEND'].dt, event2.end)
        self.assertEqual(calendar.subcomponents[1]['DESCRIPTION'],
                         f'\U0001F517 Open in Helium: {settings.PROJECT_APP_HOST}/planner/event/{event2.pk}/details')

    def _all_day_feed_components(self, user, url_name):
        response = self.client.get(
            reverse(url_name, kwargs={"private_slug": user.settings.private_slug}))
        return icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents

    def test_events_feed_all_day_uses_user_timezone_date(self):
        # GIVEN
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(
            user,
            all_day=True,
            start=datetime.datetime(2025, 9, 3, 22, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2025, 9, 4, 22, 0, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        subcomponents = self._all_day_feed_components(user, "feed_events")

        # THEN
        self.assertEqual(subcomponents[0]['DTSTART'].dt, datetime.date(2025, 9, 4))
        self.assertEqual(subcomponents[0]['DTEND'].dt, datetime.date(2025, 9, 5))

    def test_events_feed_all_day_end_is_exclusive(self):
        # GIVEN
        user = userhelper.given_a_user_exists(time_zone='America/Los_Angeles')
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(
            user,
            all_day=True,
            start=datetime.datetime(2025, 9, 4, 7, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2025, 9, 5, 7, 0, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        subcomponents = self._all_day_feed_components(user, "feed_events")

        # THEN
        self.assertEqual(subcomponents[0]['DTSTART'].dt, datetime.date(2025, 9, 4))
        self.assertEqual(subcomponents[0]['DTEND'].dt, datetime.date(2025, 9, 5))

    def test_events_feed_all_day_spanning_multiple_days(self):
        # GIVEN
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(
            user,
            all_day=True,
            start=datetime.datetime(2025, 9, 3, 22, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2025, 9, 5, 22, 0, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        subcomponents = self._all_day_feed_components(user, "feed_events")

        # THEN
        self.assertEqual(subcomponents[0]['DTSTART'].dt, datetime.date(2025, 9, 4))
        self.assertEqual(subcomponents[0]['DTEND'].dt, datetime.date(2025, 9, 6))

    def test_homework_feed_all_day_uses_user_timezone_date(self):
        # GIVEN
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(
            course,
            all_day=True,
            start=datetime.datetime(2025, 9, 3, 22, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2025, 9, 4, 22, 0, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        subcomponents = self._all_day_feed_components(user, "feed_homework")

        # THEN
        self.assertEqual(subcomponents[0]['DTSTART'].dt, datetime.date(2025, 9, 4))
        self.assertEqual(subcomponents[0]['DTEND'].dt, datetime.date(2025, 9, 5))

    def test_events_feed_with_linked_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(
            user, event, content={'ops': [{'insert': 'Note content from linked note\n'}]}
        )

        # WHEN
        response = self.client.get(reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 1)
        description = calendar.subcomponents[0]['DESCRIPTION']
        self.assertEqual(description,
                         f'\U0001F4DD Note: {settings.PROJECT_APP_HOST}/notebook/{note.pk}\n'
                         f'\U0001F517 Open in Helium: {settings.PROJECT_APP_HOST}/planner/event/{event.pk}/details')

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
        response = self.client.get(reverse("feed_homework", kwargs={"private_slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 2)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], homework1.title)
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         f'Class Info: {homework1.course.title}\n\nStatus: Complete\nGrade: 66.67%\n\n'
                         f'\U0001F517 Open in Helium: '
                         f'{settings.PROJECT_APP_HOST}/planner/assignment/{homework1.pk}/details')
        self.assertEqual(calendar.subcomponents[0]['DTSTART'].dt, homework1.start)
        self.assertEqual(calendar.subcomponents[0]['DTEND'].dt, homework1.end)
        self.assertEqual(calendar.subcomponents[1]['SUMMARY'], homework2.title)
        self.assertEqual(calendar.subcomponents[1]['DTSTART'].dt, homework2.start)
        self.assertEqual(calendar.subcomponents[1]['DTEND'].dt, homework2.end)
        self.assertEqual(calendar.subcomponents[1]['DESCRIPTION'],
                         f'Class Info: {homework2.category.title} for {homework2.course.title} '
                         f'in {homework2.course.room}\n\n\U0001F517 Open in Helium: '
                         f'{settings.PROJECT_APP_HOST}/planner/assignment/{homework2.pk}/details')

    def test_homework_feed_shows_status_only_when_complete(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group, course, category = coursehelper.given_course_with_category_exists(
            user, course_kwargs={'room': ''}, category_kwargs={'title': 'Uncategorized'})
        complete = homeworkhelper.given_homework_exists(course, category=category, title='Complete ungraded',
                                                        completed=True, current_grade="-1/100")
        incomplete = homeworkhelper.given_homework_exists(course, category=category, title='Incomplete graded',
                                                          completed=False, current_grade="20/30")

        # WHEN
        response = self.client.get(reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        descriptions = {str(component['SUMMARY']): component['DESCRIPTION'] for component in calendar.subcomponents}
        self.assertEqual(descriptions['Complete ungraded'],
                         f'Class Info: {course.title}\n\nStatus: Complete\n\n\U0001F517 Open in Helium: '
                         f'{settings.PROJECT_APP_HOST}/planner/assignment/{complete.pk}/details')
        self.assertEqual(descriptions['Incomplete graded'],
                         f'Class Info: {course.title}\n\n\U0001F517 Open in Helium: '
                         f'{settings.PROJECT_APP_HOST}/planner/assignment/{incomplete.pk}/details')

    def test_homework_feed_with_linked_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group, course, category = coursehelper.given_course_with_category_exists(
            user, course_kwargs={'room': ''}, category_kwargs={'title': 'Uncategorized'})
        homework = homeworkhelper.given_homework_exists(course, category=category)
        note = notehelper.given_note_linked_to_homework(
            user, homework, content={'ops': [{'insert': 'Homework note content\n'}]}
        )

        # WHEN
        response = self.client.get(reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 1)
        description = calendar.subcomponents[0]['DESCRIPTION']
        self.assertIn(f'\U0001F4DD Note: {settings.PROJECT_APP_HOST}/notebook/{note.pk}', description)
        self.assertNotIn('Homework note content', description)

    def test_homework_feed_with_resources(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group, course, category = coursehelper.given_course_with_category_exists(user)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group, courses=[course])
        homework = homeworkhelper.given_homework_exists(course, category=category)
        homework.resources.add(resource)

        # WHEN
        response = self.client.get(reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 1)
        description = calendar.subcomponents[0]['DESCRIPTION']
        self.assertIn(f'Resources: {resource.title}', description)

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
            reverse("feed_courseschedules", kwargs={"private_slug": user1.settings.private_slug}))

        # THEN
        calendar = icalendar.Calendar.from_ical(response.content.decode('utf-8'))
        self.assertEqual(len(calendar.subcomponents), 106)
        self.assertEqual(calendar.subcomponents[0]['SUMMARY'], course1.title)
        self.assertEqual(str(calendar.subcomponents[0]['DTSTART'].dt), '2017-01-06 02:30:00-08:00')
        self.assertEqual(str(calendar.subcomponents[0]['DTEND'].dt), '2017-01-06 05:00:00-08:00')
        self.assertEqual(calendar.subcomponents[0]['DESCRIPTION'],
                         f'Class Info: {course1.title} in {course1.room}\nClass Website: {course1.website}\n\n'
                         f'\U0001F517 Open in Helium: {settings.PROJECT_APP_HOST}/classes/{course1.pk}/schedule')

    def test_homework_feed_description_sections_details_status_and_links(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        user.settings.number_format = enums.COMMA
        user.settings.save()
        course_group, course, category = coursehelper.given_course_with_category_exists(
            user, course_kwargs={'room': 'SSC 123'}, category_kwargs={'title': 'Essay'})
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        textbook = resourcehelper.given_resource_exists(resource_group, title='Textbook', courses=[course])
        workbook = resourcehelper.given_resource_exists(resource_group, title='Workbook', courses=[course])
        homework = homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                                        current_grade='2/3')
        homework.resources.add(textbook, workbook)
        note = notehelper.given_note_linked_to_homework(user, homework)

        # WHEN
        response = self.client.get(reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        assignment_url = f'{settings.PROJECT_APP_HOST}/planner/assignment/{homework.pk}/details'
        self.assertEqual(component['DESCRIPTION'],
                         f'Class Info: Essay for {course.title} in SSC 123\nResources: Textbook, Workbook\n\n'
                         f'Status: Complete\nGrade: 66,67%\n\n'
                         f'\U0001F4DD Note: {settings.PROJECT_APP_HOST}/notebook/{note.pk}\n'
                         f'\U0001F517 Open in Helium: {assignment_url}')
        self.assertEqual(str(component['URL']), assignment_url)

    def test_homework_feed_leaves_out_the_room_of_an_online_class(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group, course, category = coursehelper.given_course_with_category_exists(
            user, course_kwargs={'room': 'SSC 123', 'is_online': True}, category_kwargs={'title': 'Uncategorized'})
        homeworkhelper.given_homework_exists(course, category=category)

        # WHEN
        response = self.client.get(reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertTrue(component['DESCRIPTION'].startswith(f'Class Info: {course.title}\n\n'))

    def test_events_feed_url_opens_the_event_in_helium(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertEqual(str(component['URL']), f'{settings.PROJECT_APP_HOST}/planner/event/{event.pk}/details')

    def test_courseschedules_feed_describes_resources_note_and_links_to_the_class(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group, room='', website='')
        courseschedulehelper.given_course_schedule_exists(course)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resourcehelper.given_resource_exists(resource_group, title='Lab Manual', courses=[course])
        note = notehelper.given_note_linked_to_course(user, course)

        # WHEN
        response = self.client.get(
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        class_url = f'{settings.PROJECT_APP_HOST}/classes/{course.pk}/schedule'
        self.assertEqual(component['DESCRIPTION'],
                         f'Class Info: {course.title}\nResources: Lab Manual\n\n'
                         f'\U0001F4DD Note: {settings.PROJECT_APP_HOST}/notebook/{note.pk}\n'
                         f'\U0001F517 Open in Helium: {class_url}')
        self.assertEqual(str(component['URL']), class_url)

    def test_courseschedules_feed_last_modified_advances_when_its_resource_is_deleted(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group, courses=[course])
        url = reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug})
        initial_response = self.client.get(url)
        initial_component = icalendar.Calendar.from_ical(initial_response.content.decode('utf-8')).subcomponents[0]

        time.sleep(1.1)

        resource.delete()

        # WHEN
        response = self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'])

        # THEN
        self.assertEqual(response.status_code, 200)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertGreater(component['SEQUENCE'], initial_component['SEQUENCE'])
        self.assertNotIn('Resources:', component['DESCRIPTION'])

    def test_new_feeds_version_makes_every_feed_download_again(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(user)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        homeworkhelper.given_homework_exists(course)
        courseschedulehelper.given_course_schedule_exists(course)
        urls = [reverse(name, kwargs={"private_slug": user.settings.private_slug})
                for name in ("feed_events", "feed_homework", "feed_courseschedules")]
        initial_responses = [self.client.get(url) for url in urls]

        # WHEN
        with self.settings(FEEDS_VERSION=settings.FEEDS_VERSION + 1):
            responses = [self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'],
                                         HTTP_IF_MODIFIED_SINCE=initial_response['Last-Modified'])
                         for url, initial_response in zip(urls, initial_responses)]

        # THEN
        for url, response in zip(urls, responses):
            with self.subTest(url=url):
                self.assertEqual(response.status_code, 200)

    def test_courseschedules_feed_last_modified_advances_when_its_note_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)
        url = reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug})
        initial_response = self.client.get(url)
        initial_component = icalendar.Calendar.from_ical(initial_response.content.decode('utf-8')).subcomponents[0]

        time.sleep(1.1)

        note = notehelper.given_note_linked_to_course(user, course)

        # WHEN
        response = self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'])

        # THEN
        self.assertEqual(response.status_code, 200)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertGreater(component['SEQUENCE'], initial_component['SEQUENCE'])
        self.assertIn(f'notebook/{note.pk}', component['DESCRIPTION'])

    def test_events_feed_returns_etag_and_last_modified_headers(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIn('Last-Modified', response)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate')
        self.assertIn(str(user.pk), response['ETag'])

    def test_events_feed_returns_etag_without_last_modified_when_empty(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()

        # WHEN
        response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertEqual(response['ETag'], f'"{user.pk}:0:{settings.FEEDS_VERSION}"')
        self.assertNotIn('Last-Modified', response)

    def test_events_feed_returns_304_on_matching_etag(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        eventhelper.given_event_exists(user)

        initial_response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # WHEN
        response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}),
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

        initial_response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))
        last_modified = initial_response['Last-Modified']

        # WHEN
        response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_MODIFIED_SINCE=last_modified)

        # THEN
        self.assertEqual(response.status_code, 304)

    def test_events_feed_returns_200_after_data_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)

        initial_response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        time.sleep(1.1)

        event.title = 'Updated Title'
        event.save()

        # WHEN
        response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)

    def test_homework_feed_returns_etag_and_last_modified_headers(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIn('Last-Modified', response)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate')

    def test_homework_feed_returns_304_on_matching_etag(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        initial_response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # WHEN
        response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}),
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
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))
        last_modified = initial_response['Last-Modified']

        # WHEN
        response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}),
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
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        time.sleep(1.1)

        homework.title = 'Updated Homework'
        homework.save()

        # WHEN
        response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)

    def test_courseschedules_feed_returns_etag_and_last_modified_headers(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        response = self.client.get(
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIn('Last-Modified', response)
        self.assertIn('Cache-Control', response)
        self.assertEqual(response['Cache-Control'], f'private, max-age={settings.FEED_ICS_MAX_AGE_SECONDS}, must-revalidate')

    def test_courseschedules_feed_returns_304_on_matching_etag(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        initial_response = self.client.get(
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        # WHEN
        response = self.client.get(
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}),
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
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}))
        last_modified = initial_response['Last-Modified']

        # WHEN
        response = self.client.get(
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}),
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
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        time.sleep(1.1)

        course.title = 'Updated Course'
        course.save()

        # WHEN
        response = self.client.get(
            reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)

    def test_events_feed_stamps_events_in_utc_with_their_last_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)
        before_request = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

        # WHEN
        response = self.client.get(reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        self.assertIn(b'DTSTAMP:', response.content)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertEqual(component['DTSTAMP'].dt.utcoffset(), datetime.timedelta(0))
        self.assertGreaterEqual(component['DTSTAMP'].dt, before_request)
        self.assertEqual(component['LAST-MODIFIED'].dt, event.updated_at.replace(microsecond=0))

    def test_events_feed_starts_an_event_at_sequence_zero_and_raises_it_when_the_event_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)
        url = reverse("feed_events", kwargs={"private_slug": user.settings.private_slug})
        initial_response = self.client.get(url)
        initial_sequence = icalendar.Calendar.from_ical(initial_response.content.decode('utf-8')).subcomponents[0][
            'SEQUENCE']

        time.sleep(1.1)

        event.start += datetime.timedelta(days=1)
        event.end += datetime.timedelta(days=1)
        event.save()

        # WHEN
        response = self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'])

        # THEN
        self.assertEqual(initial_sequence, 0)
        self.assertEqual(response.status_code, 200)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertEqual(component['SEQUENCE'], int((event.updated_at - event.created_at).total_seconds()))
        self.assertGreater(component['SEQUENCE'], initial_sequence)

    def test_homework_feed_raises_sequence_when_its_date_moves(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        url = reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug})
        initial_response = self.client.get(url)
        initial_component = icalendar.Calendar.from_ical(initial_response.content.decode('utf-8')).subcomponents[0]

        time.sleep(1.1)

        homework.start += datetime.timedelta(days=3)
        homework.end += datetime.timedelta(days=3)
        homework.save()

        # WHEN
        response = self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'])

        # THEN
        self.assertEqual(response.status_code, 200)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertEqual(component['UID'], initial_component['UID'])
        self.assertEqual(component['DTSTART'].dt, initial_component['DTSTART'].dt + datetime.timedelta(days=3))
        self.assertGreater(component['SEQUENCE'], initial_component['SEQUENCE'],
                           'Google Calendar keeps its copy of a subscribed event unless SEQUENCE rises')

    def test_homework_feed_sequence_never_falls_when_its_note_is_unlinked(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)
        url = reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug})

        time.sleep(1.1)

        note.title = 'Edited'
        note.save()
        sequence_with_edited_note = icalendar.Calendar.from_ical(
            self.client.get(url).content.decode('utf-8')).subcomponents[0]['SEQUENCE']

        time.sleep(1.1)

        note.homework.remove(homework)

        # WHEN
        response = self.client.get(url)

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertGreater(component['SEQUENCE'], sequence_with_edited_note)

    def test_homework_feed_last_modified_follows_its_class(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)
        time.sleep(1.1)
        course.room = 'SSC 456'
        course.save()

        # WHEN
        response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertEqual(component['LAST-MODIFIED'].dt, course.updated_at.replace(microsecond=0))

    def test_homework_feed_returns_200_after_resource_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group, course, category = coursehelper.given_course_with_category_exists(user)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group, courses=[course])
        homework = homeworkhelper.given_homework_exists(course, category=category)
        homework.resources.add(resource)

        initial_response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        time.sleep(1.1)

        resource.title = 'Renamed Resource'
        resource.save()

        # WHEN
        response = self.client.get(
            reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)
        self.assertIn(b'Resources: Renamed Resource', response.content)

    def test_events_feed_returns_200_after_note_linked(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)

        initial_response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}))
        etag = initial_response['ETag']

        time.sleep(1.1)

        note = notehelper.given_note_linked_to_event(user, event)

        # WHEN
        response = self.client.get(
            reverse("feed_events", kwargs={"private_slug": user.settings.private_slug}),
            HTTP_IF_NONE_MATCH=etag)

        # THEN
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)
        self.assertIn(f'notebook/{note.pk}'.encode(), response.content)

    def test_courseschedules_feed_raises_sequence_for_every_meeting_when_a_schedule_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)
        url = reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug})
        initial_components = icalendar.Calendar.from_ical(self.client.get(url).content.decode('utf-8')).subcomponents

        time.sleep(1.1)

        course_schedule.mon_start_time = datetime.time(2, 0, 0)
        course_schedule.save()

        # WHEN
        response = self.client.get(url)

        # THEN
        components = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents
        initial_sequences = {component['SEQUENCE'] for component in initial_components}
        sequences = {component['SEQUENCE'] for component in components}
        self.assertEqual(len(sequences), 1)
        self.assertGreater(sequences.pop(), max(initial_sequences))

    def test_courseschedules_feed_leaves_out_a_new_term_holiday(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)
        url = reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug})
        initial_components = icalendar.Calendar.from_ical(self.client.get(url).content.decode('utf-8')).subcomponents
        holiday = initial_components[0]['DTSTART'].dt.date()

        course_group.exceptions = holiday.strftime('%Y%m%d')
        course_group.save()

        # WHEN
        response = self.client.get(url)

        # THEN
        components = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents
        self.assertEqual(len(components), len(initial_components) - 1)
        self.assertNotIn(holiday, [component['DTSTART'].dt.date() for component in components])

    def test_courseschedules_feed_leaves_out_a_deleted_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)
        url = reverse("feed_courseschedules", kwargs={"private_slug": user.settings.private_slug})
        self.client.get(url)

        course_schedule.delete()

        # WHEN
        response = self.client.get(url)

        # THEN
        self.assertEqual(len(icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents), 0)

    def test_events_feed_last_modified_advances_when_its_note_is_deleted(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        url = reverse("feed_events", kwargs={"private_slug": user.settings.private_slug})
        initial_response = self.client.get(url)
        initial_last_modified = icalendar.Calendar.from_ical(
            initial_response.content.decode('utf-8')).subcomponents[0]['LAST-MODIFIED'].dt

        time.sleep(1.1)

        note.delete()

        # WHEN
        response = self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'])

        # THEN
        self.assertEqual(response.status_code, 200)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertGreater(component['LAST-MODIFIED'].dt, initial_last_modified)
        self.assertNotIn(f'notebook/{note.pk}', component['DESCRIPTION'])

    def test_homework_feed_last_modified_advances_when_its_note_is_unlinked(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)
        url = reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug})
        initial_last_modified = icalendar.Calendar.from_ical(
            self.client.get(url).content.decode('utf-8')).subcomponents[0]['LAST-MODIFIED'].dt

        time.sleep(1.1)

        note.homework.remove(homework)

        # WHEN
        response = self.client.get(url)

        # THEN
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertGreater(component['LAST-MODIFIED'].dt, initial_last_modified)
        self.assertNotIn(f'notebook/{note.pk}', component['DESCRIPTION'])

    def test_homework_feed_returns_200_after_resource_deleted(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.enable_private_slug()
        course_group, course, category = coursehelper.given_course_with_category_exists(user)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group, courses=[course])
        homework = homeworkhelper.given_homework_exists(course, category=category)
        homework.resources.add(resource)
        url = reverse("feed_homework", kwargs={"private_slug": user.settings.private_slug})
        initial_response = self.client.get(url)
        initial_last_modified = icalendar.Calendar.from_ical(
            initial_response.content.decode('utf-8')).subcomponents[0]['LAST-MODIFIED'].dt

        time.sleep(1.1)

        resource.delete()

        # WHEN
        response = self.client.get(url, HTTP_IF_NONE_MATCH=initial_response['ETag'])

        # THEN
        self.assertEqual(response.status_code, 200)
        component = icalendar.Calendar.from_ical(response.content.decode('utf-8')).subcomponents[0]
        self.assertGreater(component['LAST-MODIFIED'].dt, initial_last_modified)
        self.assertNotIn('Resources:', component['DESCRIPTION'])
