import datetime
import json
from types import SimpleNamespace

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.planner.models import Category, Course, CourseGroup, CourseSchedule, Event, Homework, Material, \
    MaterialGroup, Note
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, coursehelper, courseschedulehelper, \
    eventhelper, homeworkhelper, materialgrouphelper, materialhelper, notehelper, reminderhelper


def _entities(user):
    course_group = coursegrouphelper.given_course_group_exists(user)
    course = coursehelper.given_course_exists(course_group)
    schedule = courseschedulehelper.given_course_schedule_exists(course)
    category = categoryhelper.given_category_exists(course)
    homework = homeworkhelper.given_homework_exists(course)
    event = eventhelper.given_event_exists(user)
    material_group = materialgrouphelper.given_material_group_exists(user)
    material = materialhelper.given_material_exists(material_group)
    note = notehelper.given_note_exists(user)
    external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
    nested = {'course_group': course_group.pk, 'course': course.pk}

    return {
        'course group': SimpleNamespace(model=CourseGroup, pk=course_group.pk,
                                        url=reverse('planner_coursegroups_detail', kwargs={'pk': course_group.pk})),
        'course': SimpleNamespace(model=Course, pk=course.pk,
                                  url=reverse('planner_coursegroups_courses_detail',
                                              kwargs={'course_group': course_group.pk, 'pk': course.pk})),
        'course schedule': SimpleNamespace(model=CourseSchedule, pk=schedule.pk,
                                           url=reverse('planner_coursegroups_courses_courseschedules_detail',
                                                       kwargs={**nested, 'pk': schedule.pk})),
        'category': SimpleNamespace(model=Category, pk=category.pk,
                                    url=reverse('planner_coursegroups_courses_categories_detail',
                                                kwargs={**nested, 'pk': category.pk})),
        'homework': SimpleNamespace(model=Homework, pk=homework.pk,
                                    url=reverse('planner_coursegroups_courses_homework_detail',
                                                kwargs={**nested, 'pk': homework.pk})),
        'event': SimpleNamespace(model=Event, pk=event.pk,
                                 url=reverse('planner_events_detail', kwargs={'pk': event.pk})),
        'resource': SimpleNamespace(model=Material, pk=material.pk,
                                    url=reverse('planner_resourcegroups_resources_detail',
                                                kwargs={'resource_group': material_group.pk, 'pk': material.pk})),
        'resource group': SimpleNamespace(model=MaterialGroup, pk=material_group.pk,
                                          url=reverse('planner_resourcegroups_detail',
                                                      kwargs={'pk': material_group.pk})),
        'note': SimpleNamespace(model=Note, pk=note.pk, url=reverse('planner_notes_detail', kwargs={'pk': note.pk})),
        'external calendar': SimpleNamespace(model=ExternalCalendar, pk=external_calendar.pk,
                                             url=reverse('feed_externalcalendars_detail',
                                                         kwargs={'pk': external_calendar.pk})),
    }


def _changed_elsewhere(entity):
    changed_at = timezone.now() + datetime.timedelta(seconds=1)
    entity.model.objects.filter(pk=entity.pk).update(updated_at=changed_at)

    return changed_at


class TestCasePreconditions(APITestCase):
    def setUp(self):
        self.user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

    def _put(self, url, data, **headers):
        return self.client.put(url, json.dumps(data), content_type='application/json', **headers)

    def test_stale_if_match_returns_412_with_the_current_item_and_writes_nothing(self):
        for name, entity in _entities(self.user).items():
            with self.subTest(entity=name):
                # GIVEN
                read = self.client.get(entity.url).json()
                _changed_elsewhere(entity)

                # WHEN
                response = self._put(entity.url, read, HTTP_IF_MATCH=read['updated_at'])

                # THEN
                self.assertEqual(response.status_code, status.HTTP_412_PRECONDITION_FAILED)
                self.assertEqual(response.json()['id'], entity.pk)
                self.assertNotEqual(response.json()['updated_at'], read['updated_at'],
                                    'The 412 body should carry the version written elsewhere')

    def test_stale_if_match_on_delete_returns_412_and_keeps_the_item(self):
        for name, entity in _entities(self.user).items():
            with self.subTest(entity=name):
                # GIVEN
                read = self.client.get(entity.url).json()
                _changed_elsewhere(entity)

                # WHEN
                response = self.client.delete(entity.url, HTTP_IF_MATCH=read['updated_at'])

                # THEN
                self.assertEqual(response.status_code, status.HTTP_412_PRECONDITION_FAILED)
                self.assertTrue(entity.model.objects.filter(pk=entity.pk).exists())

    def test_matching_if_match_on_delete_deletes_the_item(self):
        for name in _entities(self.user):
            with self.subTest(entity=name):
                # GIVEN
                entity = _entities(self.user)[name]
                read = self.client.get(entity.url).json()

                # WHEN
                response = self.client.delete(entity.url, HTTP_IF_MATCH=read['updated_at'])

                # THEN
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(entity.model.objects.filter(pk=entity.pk).exists())

    def test_matching_if_match_updates_and_returns_the_new_version(self):
        # GIVEN
        entity = _entities(self.user)['course group']
        read = self.client.get(entity.url).json()

        # WHEN
        response = self.client.patch(entity.url, json.dumps({'title': 'Renamed'}), content_type='application/json',
                                     HTTP_IF_MATCH=read['updated_at'])

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['title'], 'Renamed')
        self.assertNotEqual(response.json()['updated_at'], read['updated_at'])

    def test_without_if_match_writes_unconditionally(self):
        # GIVEN
        entity = _entities(self.user)['course group']
        read = self.client.get(entity.url).json()
        _changed_elsewhere(entity)

        # WHEN
        response = self._put(entity.url, {**read, 'title': 'Mine'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseGroup.objects.get(pk=entity.pk).title, 'Mine')

    def test_wildcard_if_match_skips_the_check(self):
        # GIVEN
        entity = _entities(self.user)['course group']
        read = self.client.get(entity.url).json()
        _changed_elsewhere(entity)

        # WHEN
        response = self._put(entity.url, read, HTTP_IF_MATCH='*')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_weak_quoted_if_match_is_accepted(self):
        # GIVEN
        entity = _entities(self.user)['course group']
        read = self.client.get(entity.url).json()

        # WHEN
        response = self._put(entity.url, read, HTTP_IF_MATCH=f'W/"{read["updated_at"]}"')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_if_match_compares_instants_not_formatting(self):
        # GIVEN
        entity = _entities(self.user)['course group']
        whole_second = timezone.now().replace(microsecond=0)
        CourseGroup.objects.filter(pk=entity.pk).update(updated_at=whole_second)
        read = self.client.get(entity.url).json()

        # WHEN
        response = self._put(entity.url, read, HTTP_IF_MATCH=whole_second.isoformat())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         f'"{whole_second.isoformat()}" and "{read["updated_at"]}" are the same instant')

    def test_malformed_if_match_returns_400(self):
        # GIVEN
        entity = _entities(self.user)['course group']
        read = self.client.get(entity.url).json()

        # WHEN
        response = self._put(entity.url, read, HTTP_IF_MATCH='not-a-timestamp')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('If-Match', response.json())

    def test_if_match_on_another_users_item_is_still_404(self):
        # GIVEN
        other = userhelper.given_a_user_exists(username='other', email='other@example.com')
        entity = _entities(other)['course group']

        # WHEN
        response = self.client.delete(entity.url, HTTP_IF_MATCH=timezone.now().isoformat())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reminders_ignore_if_match(self):
        # GIVEN
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(self.user))
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(self.user, homework=homework, sent=True)
        url = reverse('planner_reminders_detail', kwargs={'pk': reminder.pk})

        # WHEN
        response = self.client.patch(url, json.dumps({'dismissed': True}), content_type='application/json',
                                     HTTP_IF_MATCH=(timezone.now() - datetime.timedelta(days=1)).isoformat())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         'Background jobs re-save reminders, so they are excluded from concurrency checks')

    def test_clearing_a_linked_note_with_matching_if_match_deletes_it(self):
        # GIVEN
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(self.user))
        note = notehelper.given_note_linked_to_homework(self.user, homeworkhelper.given_homework_exists(course))
        url = reverse('planner_notes_detail', kwargs={'pk': note.pk})
        read = self.client.get(url).json()

        # WHEN
        response = self.client.patch(url, json.dumps({'title': '', 'content': {'ops': [{'insert': '\n'}]}}),
                                     content_type='application/json', HTTP_IF_MATCH=read['updated_at'])

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())
