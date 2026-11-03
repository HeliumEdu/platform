import datetime

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

_BEFORE = [('planner', '0073_alter_category_weight_alter_homework_completed')]
_AFTER = [('planner', '0074_remove_comments_and_details')]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    graph = executor.loader.graph
    return executor.loader.project_state([key for key in executor.loader.applied_migrations if key in graph.nodes]).apps


class TestCaseRemoveCommentsAndDetails(TransactionTestCase):
    def setUp(self):
        self.apps = _migrate(_BEFORE)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _given_course_and_material_group(self, example_schedule=False):
        User = self.apps.get_model('helium_auth', 'User')
        CourseGroup = self.apps.get_model('planner', 'CourseGroup')
        Course = self.apps.get_model('planner', 'Course')
        MaterialGroup = self.apps.get_model('planner', 'MaterialGroup')
        user = User.objects.create(username=f'user{User.objects.count()}', email=f'u{User.objects.count()}@test.com',
                                   last_activity=timezone.now())
        course_group = CourseGroup.objects.create(title='Fall', start_date=datetime.date(2026, 8, 24),
                                                  end_date=datetime.date(2026, 12, 18), user=user,
                                                  example_schedule=example_schedule)
        course = Course.objects.create(title='Biology', credits=0, start_date=course_group.start_date,
                                       end_date=course_group.end_date, course_group=course_group)
        material_group = MaterialGroup.objects.create(title='Books', user=user, example_schedule=example_schedule)
        return user, course, material_group

    def _given_homework(self, course, comments):
        start = timezone.now()
        return self.apps.get_model('planner', 'Homework').objects.create(
            title='Lab', start=start, end=start, course=course, comments=comments)

    def test_unlinked_text_becomes_a_linked_note_and_columns_are_dropped(self):
        # GIVEN
        user, course, material_group = self._given_course_and_material_group()
        homework = self._given_homework(course, '<p>Due by <b>midnight</b></p>')
        start = timezone.now()
        event = self.apps.get_model('planner', 'Event').objects.create(
            title='Talk', start=start, end=start, user=user, comments='Slides: https://x.edu/s?a=1&b=2')
        material = self.apps.get_model('planner', 'Material').objects.create(
            title='Textbook', material_group=material_group, details='ISBN <978-1>')

        # WHEN
        apps = _migrate(_AFTER)

        # THEN
        Note = apps.get_model('planner', 'Note')
        homework_note = Note.objects.get(homework__id=homework.pk)
        self.assertEqual(homework_note.content['ops'][1], {'insert': 'midnight', 'attributes': {'bold': True}})
        self.assertEqual(homework_note.user_id, user.pk)
        self.assertEqual(Note.objects.get(events__id=event.pk).content,
                         {'ops': [{'insert': 'Slides: https://x.edu/s?a=1&b=2\n'}]})
        self.assertEqual(Note.objects.get(resources__id=material.pk).content,
                         {'ops': [{'insert': 'ISBN <978-1>\n'}]})
        homework_columns = [c.name for c in connection.introspection.get_table_description(
            connection.cursor(), 'planner_homework')]
        self.assertNotIn('comments', homework_columns)

    def test_items_already_linked_to_a_note_or_without_text_get_no_new_note(self):
        # GIVEN
        user, course, _ = self._given_course_and_material_group()
        linked = self._given_homework(course, 'Already converted')
        Note = self.apps.get_model('planner', 'Note')
        Note.objects.create(title='', content={'ops': [{'insert': 'Already converted\n'}]}, user=user).homework.add(
            linked)
        self._given_homework(course, '')
        self._given_homework(course, '   \n')

        # WHEN
        apps = _migrate(_AFTER)

        # THEN
        self.assertEqual(apps.get_model('planner', 'Note').objects.count(), 1)

    def test_note_follows_the_example_schedule_flag_of_its_item(self):
        # GIVEN
        _, course, _ = self._given_course_and_material_group(example_schedule=True)
        homework = self._given_homework(course, 'Seeded text')

        # WHEN
        apps = _migrate(_AFTER)

        # THEN
        self.assertTrue(apps.get_model('planner', 'Note').objects.get(homework__id=homework.pk).example_schedule)
