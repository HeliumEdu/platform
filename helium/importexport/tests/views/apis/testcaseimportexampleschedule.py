import datetime
import json
from unittest import mock
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.importexport.tests.helpers import exampleschedulehelper
from helium.planner.models import CourseGroup, Course, Homework, Category, CourseSchedule, Event, Resource, \
    ResourceGroup, Note, Reminder


_COUNTED_MODELS = (CourseGroup, Course, Category, CourseSchedule, Homework, Event, ResourceGroup, Resource, Note)


def _row_counts(user):
    return exampleschedulehelper.count_rows_by_model(user, _COUNTED_MODELS)


class TestCaseImportExampleSchedule(APITestCase):
    def setUp(self):
        self.enterContext(mock.patch('helium.auth.services.authservice.send_analytics_event.apply_async'))
        self.enterContext(mock.patch('helium.auth.services.authservice.metricutils.timing'))

    def test_second_import_without_clearing_is_rejected_and_adds_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        self.assertEqual(exampleschedulehelper.post_import_example_schedule(self.client).status_code,
                         status.HTTP_204_NO_CONTENT)
        counts_after_first_import = _row_counts(user)

        # WHEN
        response = exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         ['The example schedule has already been imported. Please clear it before importing it '
                          'again.'])
        self.assertEqual(_row_counts(user), counts_after_first_import)

    def test_import_failure_releases_the_claim_so_the_import_can_be_retried(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)

        # WHEN
        with mock.patch('helium.importexport.views.apis.importviews.examplescheduleimportservice.import_example_schedule',
                        side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.show_getting_started)
        self.assertEqual(exampleschedulehelper.post_import_example_schedule(self.client).status_code,
                         status.HTTP_204_NO_CONTENT)

    def test_clear_right_after_import_deletes_everything(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        self.assertEqual(exampleschedulehelper.post_import_example_schedule(self.client).status_code,
                         status.HTTP_204_NO_CONTENT)

        # WHEN
        response = exampleschedulehelper.delete_example_schedule(self.client)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(sum(_row_counts(user).values()), 0)

    def test_clear_after_editing_the_imported_example_schedule_keeps_only_the_edited_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        self.assertEqual(exampleschedulehelper.post_import_example_schedule(self.client).status_code,
                         status.HTTP_204_NO_CONTENT)
        homework = Homework.objects.for_user(user.pk).first()
        homework.title = 'Renamed by me'
        homework.save()
        kept_course_homework_count = Homework.objects.filter(course=homework.course).count()

        # WHEN
        response = exampleschedulehelper.delete_example_schedule(self.client)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([course.pk for course in Course.objects.for_user(user.pk)], [homework.course_id])
        self.assertEqual(Homework.objects.for_user(user.pk).count(), kept_course_homework_count)
        self.assertTrue(Homework.objects.filter(pk=homework.pk, title='Renamed by me').exists())
        self.assertEqual(Event.objects.for_user(user.pk).count(), 0)

    def test_reimport_after_a_partial_clear_leaves_the_kept_work_alone_and_isolates_the_new_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        example = exampleschedulehelper.given_example_schedule_exists(user)
        example.homework.title = 'Renamed by me'
        example.homework.save()
        self.assertEqual(exampleschedulehelper.delete_example_schedule(self.client).status_code, status.HTTP_200_OK)
        kept_course_group = CourseGroup.objects.get(pk=example.course_group.pk)
        kept_updated_at = kept_course_group.updated_at
        kept_homework_updated_at = Homework.objects.get(pk=example.homework.pk).updated_at

        # WHEN
        reimport_response = exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        self.assertEqual(reimport_response.status_code, status.HTTP_204_NO_CONTENT)
        new_course_group = CourseGroup.objects.exclude(pk=example.course_group.pk).get()
        self.assertTrue(new_course_group.example_schedule)
        self.assertFalse(CourseGroup.objects.get(pk=example.course_group.pk).example_schedule)
        self.assertEqual(CourseGroup.objects.get(pk=example.course_group.pk).updated_at, kept_updated_at)
        self.assertEqual(Homework.objects.get(pk=example.homework.pk).updated_at, kept_homework_updated_at)

        # WHEN
        second_clear_response = exampleschedulehelper.delete_example_schedule(self.client)

        # THEN
        self.assertEqual(second_clear_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CourseGroup.objects.filter(pk=new_course_group.pk).exists())
        self.assertTrue(CourseGroup.objects.filter(pk=example.course_group.pk).exists())
        self.assertTrue(Homework.objects.filter(pk=example.homework.pk, title='Renamed by me').exists())

    def test_reimport_promotes_an_edited_example_root_so_the_new_stamp_cannot_hide_the_edit(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        example = exampleschedulehelper.given_example_schedule_exists(user)
        example.homework.title = 'Renamed by me'
        example.homework.save()
        exampleschedulehelper.given_example_import_allowed(user)

        # WHEN
        self.assertEqual(exampleschedulehelper.post_import_example_schedule(self.client).status_code,
                         status.HTTP_204_NO_CONTENT)

        # THEN
        self.assertFalse(CourseGroup.objects.get(pk=example.course_group.pk).example_schedule)
        user.refresh_from_db()
        self.assertGreater(user.example_schedule_imported_at, example.imported_at)
        self.assertEqual(user.example_schedule_first_imported_at, example.imported_at,
                         'the first import time never moves, so metrics keep counting work from before the re-import')

        # WHEN
        response = exampleschedulehelper.delete_example_schedule(self.client)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Homework.objects.filter(pk=example.homework.pk, title='Renamed by me').exists())
        self.assertTrue(CourseGroup.objects.filter(pk=example.course_group.pk).exists())
        self.assertFalse(Event.objects.filter(pk=example.event.pk).exists())


class TestCaseImportExampleScheduleViews(APITestCase):
    def test_user_setup_imports_example_schedule(self):
        # GIVEN
        register_response = self.client.post(reverse('auth_user_resource_register'),
                                             json.dumps({'email': 'test@test.com', 'username': 'my_test_user',
                                                         'password': 'test_pass_1!',
                                                         'time_zone': 'America/Chicago'}),
                                             content_type='application/json', HTTP_X_CLIENT_VERSION='3.9.5')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CourseGroup.objects.count(), 0)
        user = get_user_model().objects.get(email='test@test.com')
        user.is_active = True
        user.save()
        userhelper.reauthenticate(self.client, user)

        # WHEN
        response = self.client.post(reverse('auth_user_setup'), json.dumps({}), content_type='application/json')

        user_tz = ZoneInfo('America/Chicago')
        now = timezone.now().astimezone(user_tz)
        adjusted_month = now.month - 1
        adjusted_year = now.year
        if adjusted_month == 0:
            adjusted_month = 12
            adjusted_year -= 1

        adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0,
                                     second=0, microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['setup_state'], enums.SETUP_COMPLETE)
        start_of_month = adjusted_month.replace(day=first_monday.day, hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(CourseSchedule.objects.count(), 3)
        self.assertEqual(Category.objects.count(), 15)
        self.assertEqual(ResourceGroup.objects.count(), 3)
        self.assertEqual(Resource.objects.count(), 5)
        self.assertEqual(Homework.objects.count(), 53)
        self.assertEqual(Reminder.objects.count(), 9)
        self.assertEqual(Event.objects.count(), 9)

        homework1 = Homework.objects.all()[0]
        self.assertEqual(CourseGroup.objects.all()[0].start_date, start_of_month.date())
        self.assertEqual(Course.objects.all()[0].start_date, start_of_month.date())
        self.assertEqual(homework1.start.date(), homework1.course.start_date + datetime.timedelta(
            days=(homework1.start.date() - homework1.course.start_date).days))
        reminder = Reminder.objects.filter(event__isnull=False).first()
        self.assertEqual(reminder.start_of_range.date(), reminder.event.start.date())

        fourth_friday = first_monday + relativedelta(days=4, weeks=3)
        event = Event.objects.all()[4]
        self.assertEqual(event.start.date(), fourth_friday.date())
        self.assertEqual(event.end.date(), fourth_friday.date() + relativedelta(days=3))

        course_group = CourseGroup.objects.all()[0]
        course = Course.objects.for_course_group(course_group.pk)[1]
        category1 = Category.objects.for_course(course.pk)[2]
        category2 = Category.objects.for_course(course.pk)[4]
        self.assertEqual(float(course_group.overall_grade), 88.035)
        self.assertEqual(float(course_group.trend), 0.001242953846153782)
        self.assertEqual(float(course.current_grade), 87.8286)
        self.assertEqual(float(course.trend), 0.005750234265734315)
        self.assertEqual(float(category1.average_grade), 110)
        self.assertEqual(float(category1.grade_by_weight), 16.5)
        self.assertIsNone(category1.trend)
        self.assertEqual(float(category2.average_grade), 87.6)
        self.assertEqual(float(category2.grade_by_weight), 17.52)
        self.assertEqual(float(category2.trend), 0.011699999999999875)

        # 1 standalone + 29 linked = 30
        self.assertEqual(Note.objects.count(), 30)

        # 1 welcome + 8 events + 15 homework = 24 (resources have blank titles)
        titled_notes = Note.objects.exclude(title='')
        self.assertEqual(titled_notes.count(), 24)

        homework_with_notes = Homework.objects.filter(notes_set__isnull=False).distinct()
        self.assertGreater(homework_with_notes.count(), 0)

    def _local_hours_after_example_import(self, time_zone):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone=time_zone)
        exampleschedulehelper.given_example_import_allowed(user)

        exampleschedulehelper.post_import_example_schedule(self.client)

        user_tz = ZoneInfo(time_zone)
        course = Course.objects.get(title='Fundamentals of Programming 💻')
        schedule = CourseSchedule.objects.get(course=course)
        homework = (Homework.objects.filter(course=course, all_day=False)
                    .order_by('start').first())
        return schedule.mon_start_time, homework.start.astimezone(user_tz).time()

    def test_example_schedule_lands_at_the_same_local_time_in_every_zone(self):
        # GIVEN / WHEN
        la_class, la_homework = self._local_hours_after_example_import('America/Los_Angeles')
        User = get_user_model()
        User.objects.all().delete()
        tokyo_class, tokyo_homework = self._local_hours_after_example_import('Asia/Tokyo')

        # THEN
        self.assertEqual(la_class, tokyo_class,
                         msg='the example schedule reads the same wall clock in every zone')
        self.assertEqual(la_homework, tokyo_homework)

    def test_example_schedule_class_and_homework_times_agree(self):
        # GIVEN / WHEN
        class_time, homework_time = self._local_hours_after_example_import('Europe/Amsterdam')

        # THEN
        self.assertEqual(class_time, datetime.time(11, 0))
        self.assertEqual(homework_time, datetime.time(11, 0),
                         msg='an assignment authored at class time stays at class time')

    def test_import_exampleschedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)

        # WHEN
        response = exampleschedulehelper.post_import_example_schedule(self.client)

        # GIVEN
        user_tz = ZoneInfo('America/Los_Angeles')
        now = timezone.now().astimezone(user_tz)
        adjusted_month = now.month - 1
        adjusted_year = now.year
        if adjusted_month == 0:
            adjusted_month = 12
            adjusted_year -= 1

        adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0, second=0,
                                     microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)
        first_monday_date = first_monday.date()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # --- Entity counts ---
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(CourseSchedule.objects.count(), 3)
        self.assertEqual(Category.objects.count(), 15)
        self.assertEqual(ResourceGroup.objects.count(), 3)
        self.assertEqual(Resource.objects.count(), 5)
        self.assertEqual(Homework.objects.count(), 53)
        self.assertEqual(Event.objects.count(), 9)
        # 8 from fixture + 1 created by create_next_repeating_reminder for the course reminder
        self.assertEqual(Reminder.objects.count(), 9)
        # 1 standalone + 29 linked = 30
        self.assertEqual(Note.objects.count(), 30)

        # --- CourseGroup ---
        course_group = CourseGroup.objects.first()
        self.assertEqual(course_group.title, 'Fall Semester')
        self.assertEqual(course_group.start_date, first_monday_date)
        self.assertTrue(course_group.shown_on_calendar)
        self.assertEqual(float(course_group.overall_grade), 88.035)
        self.assertAlmostEqual(course_group.trend, 0.00124295384615381)
        self.assertTrue(course_group.example_schedule)
        self.assertEqual(course_group.user, user)

        # --- Courses (ordered by start_date, title) ---
        courses = list(Course.objects.all())
        self.assertEqual(len(courses), 3)

        course_titles = {c.title for c in courses}
        self.assertEqual(course_titles, {'Creative Writing ✍️', 'Fundamentals of Programming 💻', 'Intro to Psychology 🧠'})

        creative_writing = Course.objects.get(title='Creative Writing ✍️')
        self.assertEqual(creative_writing.room, 'ARTS 302')
        self.assertEqual(float(creative_writing.credits), 3.0)
        self.assertEqual(creative_writing.color, '#bd42a4')
        self.assertFalse(creative_writing.is_online)
        self.assertEqual(float(creative_writing.current_grade), 89.95)
        self.assertAlmostEqual(creative_writing.trend, -0.0004915000000000664)
        self.assertEqual(creative_writing.teacher_name, 'Dr. Joey Rubik')
        self.assertEqual(creative_writing.teacher_email, 'joey.rubik@university.edu')
        self.assertEqual(creative_writing.start_date, first_monday_date)
        self.assertEqual(creative_writing.course_group, course_group)

        programming = Course.objects.get(title='Fundamentals of Programming 💻')
        self.assertEqual(programming.room, '')
        self.assertEqual(float(programming.credits), 3.0)
        self.assertEqual(programming.color, '#05cc90')
        self.assertEqual(programming.website, 'https://automatetheboringstuff.com')
        self.assertTrue(programming.is_online)
        self.assertEqual(float(programming.current_grade), 87.8286)
        self.assertAlmostEqual(programming.trend, 0.005750234265734248)
        self.assertEqual(programming.teacher_name, 'Dr. Alex Gallagher')
        self.assertEqual(programming.teacher_email, 'alex.gallagher@university.edu')
        self.assertEqual(programming.start_date, first_monday_date)

        psychology = Course.objects.get(title='Intro to Psychology 🧠')
        self.assertEqual(psychology.room, 'SOC 110')
        self.assertEqual(float(psychology.credits), 4.0)
        self.assertEqual(psychology.color, '#3033cf')
        self.assertFalse(psychology.is_online)
        self.assertEqual(float(psychology.current_grade), 86.3264)
        self.assertAlmostEqual(psychology.trend, 0.02126585714285706)
        self.assertEqual(psychology.teacher_name, 'Dr. Jess Otter')
        self.assertEqual(psychology.teacher_email, 'jess.otter@university.edu')

        # --- CourseSchedules ---
        cw_schedule = CourseSchedule.objects.get(course=creative_writing)
        self.assertEqual(cw_schedule.days_of_week, '0010100')
        self.assertEqual(cw_schedule.tue_start_time, datetime.time(11, 0))
        self.assertEqual(cw_schedule.tue_end_time, datetime.time(11, 50))
        self.assertEqual(cw_schedule.thu_start_time, datetime.time(11, 0))
        self.assertEqual(cw_schedule.thu_end_time, datetime.time(11, 50))

        prog_schedule = CourseSchedule.objects.get(course=programming)
        self.assertEqual(prog_schedule.days_of_week, '0101010')
        self.assertEqual(prog_schedule.mon_start_time, datetime.time(11, 0))
        self.assertEqual(prog_schedule.mon_end_time, datetime.time(11, 50))

        psych_schedule = CourseSchedule.objects.get(course=psychology)
        self.assertEqual(psych_schedule.days_of_week, '0101010')
        self.assertEqual(psych_schedule.mon_start_time, datetime.time(13, 0))
        self.assertEqual(psych_schedule.mon_end_time, datetime.time(13, 50))

        # --- Categories (4 + 5 + 6 = 15) ---
        cw_categories = Category.objects.filter(course=creative_writing).order_by('title')
        self.assertEqual(cw_categories.count(), 4)
        cw_cat_titles = list(cw_categories.values_list('title', flat=True))
        self.assertEqual(cw_cat_titles, ['Essay 📝', 'Final Portfolio 📚', 'Reading 📖', 'Short Stories 🪶'])

        essay_cat = cw_categories.get(title='Essay 📝')
        self.assertEqual(float(essay_cat.weight), 40.0)
        self.assertEqual(essay_cat.color, '#c964b5')
        self.assertEqual(float(essay_cat.average_grade), 88.6)
        self.assertEqual(float(essay_cat.grade_by_weight), 35.44)
        self.assertAlmostEqual(essay_cat.trend, -0.022299999999999975)

        reading_cat = cw_categories.get(title='Reading 📖')
        self.assertEqual(float(reading_cat.weight), 0.0)
        self.assertEqual(float(reading_cat.average_grade), -1.0)
        self.assertEqual(float(reading_cat.grade_by_weight), 0.0)

        prog_categories = Category.objects.filter(course=programming).order_by('title')
        self.assertEqual(prog_categories.count(), 5)
        prog_cat_titles = list(prog_categories.values_list('title', flat=True))
        self.assertEqual(prog_cat_titles, ['Final Exam 📈', 'Homework 👨🏽‍💻', 'Midterm 📊', 'Project 🔨', 'Quiz 💡'])

        midterm_cat = prog_categories.get(title='Midterm 📊')
        self.assertEqual(float(midterm_cat.weight), 15.0)
        self.assertEqual(float(midterm_cat.average_grade), 110.0)
        self.assertEqual(float(midterm_cat.grade_by_weight), 16.5)
        self.assertIsNone(midterm_cat.trend)

        quiz_cat = prog_categories.get(title='Quiz 💡')
        self.assertEqual(float(quiz_cat.weight), 20.0)
        self.assertEqual(float(quiz_cat.average_grade), 87.6)
        self.assertEqual(float(quiz_cat.grade_by_weight), 17.52)
        self.assertAlmostEqual(quiz_cat.trend, 0.011699999999999875)

        psych_categories = Category.objects.filter(course=psychology).order_by('title')
        self.assertEqual(psych_categories.count(), 6)
        psych_cat_titles = list(psych_categories.values_list('title', flat=True))
        self.assertEqual(psych_cat_titles, ['Capstone Case Study 🧩', 'Case Study 🔎', 'Final Exam 📈', 'Midterm 📊',
                                            'Quiz 💡', 'Reading 📖'])

        # Verify cumulative weights per course don't exceed 100
        for course in courses:
            total_weight = sum(float(c.weight) for c in Category.objects.filter(course=course))
            self.assertLessEqual(total_weight, 100.0)

        # --- ResourceGroups ---
        resource_groups = ResourceGroup.objects.all().order_by('title')
        self.assertEqual(resource_groups.count(), 3)
        resource_group_titles = list(resource_groups.values_list('title', flat=True))
        self.assertEqual(resource_group_titles, ['Digital Tools', 'Supplies', 'Textbooks'])
        for resource_group in resource_groups:
            self.assertTrue(resource_group.shown_on_calendar)
            self.assertTrue(resource_group.example_schedule)
            self.assertEqual(resource_group.user, user)

        # --- Resources ---
        resources = Resource.objects.all().order_by('title')
        self.assertEqual(resources.count(), 5)

        automate = resources.get(title='Automate the Boring Stuff with Python')
        self.assertEqual(automate.price, '$28.99')
        self.assertEqual(automate.resource_group, resource_groups.get(title='Textbooks'))
        self.assertEqual(list(automate.courses.values_list('title', flat=True)), ['Fundamentals of Programming 💻'])

        google = resources.get(title='Google Workspace (Docs, Drive)')
        self.assertEqual(google.price, 'Free')
        self.assertEqual(google.status, 7)
        self.assertEqual(google.condition, 8)
        self.assertEqual(google.resource_group, resource_groups.get(title='Digital Tools'))
        self.assertEqual(google.courses.count(), 3)

        notebook = resources.get(title='Notebook 📓')
        self.assertEqual(notebook.price, '$5.00')
        self.assertEqual(notebook.resource_group, resource_groups.get(title='Supplies'))
        self.assertEqual(notebook.courses.count(), 2)
        self.assertFalse(notebook.courses.filter(title='Fundamentals of Programming 💻').exists())

        bird = resources.get(title='Bird by Bird: Some Instructions on Writing and Life')
        self.assertEqual(bird.price, '$16.00')
        self.assertEqual(bird.status, 1)
        self.assertEqual(list(bird.courses.values_list('title', flat=True)), ['Creative Writing ✍️'])

        psych_textbook = resources.get(title='Psychology, 14th Edition')
        self.assertEqual(psych_textbook.price, '$45.00')
        self.assertEqual(list(psych_textbook.courses.values_list('title', flat=True)), ['Intro to Psychology 🧠'])

        # --- Events ---
        events = Event.objects.all()
        self.assertEqual(events.count(), 9)

        event_titles = list(events.values_list('title', flat=True))
        self.assertIn('Writing Workshop', event_titles)
        self.assertIn('Group Meeting (Programming)', event_titles)
        self.assertIn('Parents Weekend', event_titles)
        self.assertIn('Study Session (Midterm, Programming)', event_titles)
        self.assertIn('Study Session (Final, Psych)', event_titles)
        self.assertIn('Study Session (Final, Programming)', event_titles)
        self.assertIn('Final Portfolio Writing Workshop', event_titles)
        self.assertEqual(event_titles.count('Writing Workshop'), 3)

        parents_weekend = events.get(title='Parents Weekend')
        self.assertTrue(parents_weekend.all_day)
        self.assertEqual(parents_weekend.priority, 50)
        self.assertTrue(parents_weekend.example_schedule)
        self.assertEqual(parents_weekend.user, user)

        study_midterm = events.get(title='Study Session (Midterm, Programming)')
        self.assertFalse(study_midterm.all_day)
        self.assertTrue(study_midterm.show_end_time)
        self.assertEqual(study_midterm.priority, 60)
        self.assertIsNone(study_midterm.owner_id)
        self.assertEqual(study_midterm.user, user)

        for event in events:
            self.assertTrue(event.example_schedule)
            self.assertEqual(event.user, user)

        # --- Homework ---
        all_homework = Homework.objects.all()
        self.assertEqual(all_homework.count(), 53)
        self.assertEqual(all_homework.filter(completed=True).count(), 35)
        self.assertEqual(all_homework.filter(completed=False).count(), 18)

        graded_hw = [h for h in all_homework if h.current_grade and '/' in h.current_grade
                     and not h.current_grade.startswith('-1/')]
        self.assertEqual(len(graded_hw), 25)

        # Verify every homework belongs to one of the imported courses and has a category
        for hw in all_homework:
            self.assertIn(hw.course, courses)
            self.assertIsNotNone(hw.category)

        # Verify homework-resource M2M relationships
        hw_with_resources = all_homework.filter(resources__isnull=False).distinct()
        self.assertEqual(hw_with_resources.count(), 53)

        # Verify completed homework has completed_at set
        for hw in all_homework.filter(completed=True):
            self.assertIsNotNone(hw.completed_at)

        # Spot-check specific homework
        essay1_list = list(Homework.objects.filter(title='Essay 1'))
        self.assertEqual(len(essay1_list), 1)
        essay1 = essay1_list[0]
        self.assertFalse(essay1.all_day)
        self.assertFalse(essay1.show_end_time)
        self.assertEqual(essay1.priority, 46)
        self.assertEqual(essay1.current_grade, '95/100')
        self.assertTrue(essay1.completed)
        self.assertIsNotNone(essay1.completed_at)
        self.assertEqual(essay1.course, creative_writing)
        self.assertEqual(essay1.category, essay_cat)
        self.assertEqual(essay1.resources.count(), 2)
        self.assertTrue(essay1.resources.filter(title='Google Workspace (Docs, Drive)').exists())
        self.assertTrue(essay1.resources.filter(title='Notebook 📓').exists())
        self.assertTrue(essay1.notes_set.exists())
        essay1_note = essay1.notes_set.filter(title='').first()
        self.assertIsNotNone(essay1_note)
        self.assertIn('ops', essay1_note.content)

        midterm_prog = Homework.objects.get(title='Midterm', course=programming)
        self.assertEqual(midterm_prog.current_grade, '55/50')
        self.assertTrue(midterm_prog.completed)
        self.assertEqual(midterm_prog.category, midterm_cat)

        # Verify date adjustment: all homework dates are relative to first_monday
        for hw in all_homework.select_related('course'):
            self.assertGreaterEqual(hw.start.date(), hw.course.start_date)

        # --- Reminders ---
        all_reminders = Reminder.objects.all()
        self.assertEqual(all_reminders.count(), 9)

        hw_reminders = all_reminders.filter(homework__isnull=False)
        event_reminders = all_reminders.filter(event__isnull=False)
        course_reminders = all_reminders.filter(course__isnull=False)
        self.assertEqual(hw_reminders.count(), 6)
        self.assertEqual(event_reminders.count(), 1)
        self.assertGreaterEqual(course_reminders.count(), 1)

        # Verify every reminder belongs to the user and has exactly one parent
        for reminder in all_reminders:
            self.assertEqual(reminder.user, user)
            parents = sum([
                reminder.homework_id is not None,
                reminder.event_id is not None,
                reminder.course_id is not None,
            ])
            self.assertEqual(parents, 1)

        # Event reminder: a single Push (type 3)
        for reminder in event_reminders:
            self.assertEqual(reminder.event, study_midterm)
            self.assertEqual(reminder.message, 'Bring notes for group')
            self.assertEqual(reminder.message, 'Bring notes for group')
            self.assertEqual(reminder.offset, 30)
            self.assertEqual(reminder.offset_type, 0)
            self.assertTrue(reminder.sent)
            self.assertFalse(reminder.dismissed)
        event_reminder_types = set(event_reminders.values_list('type', flat=True))
        self.assertEqual(event_reminder_types, {3})

        # Course reminder should reference Creative Writing
        course_reminder = course_reminders.filter(sent=True).first()
        self.assertIsNotNone(course_reminder)
        self.assertEqual(course_reminder.course, creative_writing)
        self.assertEqual(course_reminder.message, 'Class starts soon')
        self.assertEqual(course_reminder.message, 'Class starts soon')
        self.assertEqual(course_reminder.offset, 10)
        self.assertEqual(course_reminder.offset_type, 0)
        self.assertEqual(course_reminder.type, 3)
        self.assertTrue(course_reminder.sent)

        # Homework reminders: verify start_of_range is computed relative to the homework start
        for reminder in hw_reminders:
            self.assertIsNotNone(reminder.start_of_range)

        # --- Notes ---
        all_notes = Note.objects.all()
        self.assertEqual(all_notes.count(), 30)

        # Standalone notes (no entity links)
        standalone_notes = Note.objects.filter(
            homework__isnull=True
        ).filter(
            events__isnull=True
        ).filter(
            resources__isnull=True
        )
        self.assertEqual(standalone_notes.count(), 1)
        welcome_note = standalone_notes.first()
        self.assertEqual(welcome_note.title, 'A Study Session Template')
        self.assertIn('ops', welcome_note.content)
        self.assertTrue(welcome_note.example_schedule)
        self.assertEqual(welcome_note.user, user)

        # Titled notes: 1 welcome + 8 events + 15 homework = 24
        titled_notes = Note.objects.exclude(title='')
        self.assertEqual(titled_notes.count(), 24)

        # Untitled notes: 5 resource links + 1 homework link = 6
        untitled_notes = Note.objects.filter(title='')
        self.assertEqual(untitled_notes.count(), 6)

        # Notes linked to homework
        hw_notes = Note.objects.filter(homework__isnull=False).distinct()
        self.assertEqual(hw_notes.count(), 16)

        # Notes linked to events
        event_notes = Note.objects.filter(events__isnull=False).distinct()
        self.assertEqual(event_notes.count(), 8)

        sprint_note = Note.objects.filter(title='Sprint Planning').first()
        self.assertIsNotNone(sprint_note)
        self.assertTrue(sprint_note.events.exists())
        self.assertIn('ops', sprint_note.content)

        # Notes linked to resources
        resource_notes = Note.objects.filter(resources__isnull=False).distinct()
        self.assertEqual(resource_notes.count(), 5)
        for note in resource_notes:
            self.assertIn('ops', note.content)

        notebook_untitled_notes = notebook.notes_set.filter(title='')
        self.assertEqual(notebook_untitled_notes.count(), 1)
        notebook_note = notebook_untitled_notes.first()
        self.assertIn('ops', notebook_note.content)

        # All notes should be marked as example_schedule and belong to user
        for note in all_notes:
            self.assertTrue(note.example_schedule)
            self.assertEqual(note.user, user)

        # --- User settings ---
        user.settings.refresh_from_db()
        self.assertTrue(user.settings.show_getting_started)

        # --- Import stamp ---
        user.refresh_from_db()
        self.assertIsNotNone(user.example_schedule_imported_at)
        self.assertEqual(user.example_schedule_first_imported_at, user.example_schedule_imported_at)
        for model in (CourseGroup, Course, CourseSchedule, Category, ResourceGroup, Resource, Event, Homework, Note):
            for row in model.objects.for_user(user.pk):
                self.assertLessEqual(row.updated_at, user.example_schedule_imported_at,
                                     msg=f'{model.__name__} {row.pk} was written after the stamp')

    def test_reimport_exampleschedule_after_dismiss_all_does_not_touch_prior_import(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        first_response = exampleschedulehelper.post_import_example_schedule(self.client)
        self.assertEqual(first_response.status_code, status.HTTP_204_NO_CONTENT)

        first_course_group = CourseGroup.objects.get()
        first_homework_ids = set(Homework.objects.values_list('pk', flat=True))
        first_event_ids = set(Event.objects.values_list('pk', flat=True))
        first_reminder_ids = set(Reminder.objects.values_list('pk', flat=True))

        # GIVEN
        # The user dismisses all of their sent reminders from the first import, via the same
        # dismiss-all-reminders endpoint the app uses for notifications
        dismiss_response = self.client.patch(reverse('planner_reminders_dismiss_all') + '?sent=true')
        self.assertEqual(dismiss_response.status_code, status.HTTP_204_NO_CONTENT)
        dismissed_reminders = Reminder.objects.filter(pk__in=first_reminder_ids, sent=True)
        self.assertTrue(dismissed_reminders.exists())
        self.assertTrue(all(dismissed_reminders.values_list('dismissed', flat=True)))

        # GIVEN
        # A snapshot of the first import's state immediately before the second import, so the
        # second import's date adjustments can be proven not to have touched any of it
        first_course_group_snapshot = (
            first_course_group.start_date, first_course_group.end_date, first_course_group.updated_at)
        first_homework_snapshot = {
            h.pk: (h.start, h.end, h.updated_at) for h in Homework.objects.filter(pk__in=first_homework_ids)
        }
        first_event_snapshot = {
            e.pk: (e.start, e.end, e.updated_at) for e in Event.objects.filter(pk__in=first_event_ids)
        }
        first_reminder_snapshot = {
            r.pk: (r.start_of_range, r.sent, r.dismissed, r.updated_at)
            for r in Reminder.objects.filter(pk__in=first_reminder_ids)
        }

        # WHEN
        exampleschedulehelper.given_example_schedule_became_user_data(user)
        second_response = exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        # No server error occurs
        self.assertEqual(second_response.status_code, status.HTTP_204_NO_CONTENT)

        # THEN
        # A second, independent CourseGroup was created for the new import
        self.assertEqual(CourseGroup.objects.count(), 2)
        self.assertTrue(CourseGroup.objects.exclude(pk=first_course_group.pk).exists())

        # THEN
        # The first import's CourseGroup dates/timestamp are untouched
        first_course_group.refresh_from_db()
        self.assertEqual(
            (first_course_group.start_date, first_course_group.end_date, first_course_group.updated_at),
            first_course_group_snapshot)

        # THEN
        # The first import's Homework rows are untouched
        for homework in Homework.objects.filter(pk__in=first_homework_ids):
            self.assertEqual((homework.start, homework.end, homework.updated_at),
                             first_homework_snapshot[homework.pk])

        # THEN
        # The first import's Event rows are untouched
        for event in Event.objects.filter(pk__in=first_event_ids):
            self.assertEqual((event.start, event.end, event.updated_at),
                             first_event_snapshot[event.pk])

        # THEN
        # The first import's (already-dismissed) Reminder rows are untouched — in particular,
        # `sent` was never reset to False on a dismissed reminder, which is what tripped the
        # `reminder_dismissed_requires_sent` constraint in the original incident
        for reminder in Reminder.objects.filter(pk__in=first_reminder_ids):
            self.assertEqual(
                (reminder.start_of_range, reminder.sent, reminder.dismissed, reminder.updated_at),
                first_reminder_snapshot[reminder.pk])

    def test_reimport_exampleschedule_after_dismiss_all_succeeds_and_adds_second_group(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        first_response = exampleschedulehelper.post_import_example_schedule(self.client)
        self.assertEqual(first_response.status_code, status.HTTP_204_NO_CONTENT)
        first_course_group = CourseGroup.objects.get()

        # GIVEN
        # The user dismisses all of their sent reminders from the first import
        dismiss_response = self.client.patch(reverse('planner_reminders_dismiss_all') + '?sent=true')
        self.assertEqual(dismiss_response.status_code, status.HTTP_204_NO_CONTENT)

        # WHEN
        exampleschedulehelper.given_example_schedule_became_user_data(user)
        second_response = exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        # No server error occurs
        self.assertEqual(second_response.status_code, status.HTTP_204_NO_CONTENT)

        # THEN
        # A second, independent CourseGroup was created for the new import
        self.assertEqual(CourseGroup.objects.count(), 2)
        self.assertTrue(CourseGroup.objects.exclude(pk=first_course_group.pk).exists())

    def test_reimport_exampleschedule_after_dismiss_all_still_rebases_the_new_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)
        exampleschedulehelper.post_import_example_schedule(self.client)
        first_course_group = CourseGroup.objects.get()
        self.client.patch(reverse('planner_reminders_dismiss_all') + '?sent=true')

        # WHEN
        exampleschedulehelper.given_example_schedule_became_user_data(user)
        response = exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        second_course_group = CourseGroup.objects.exclude(pk=first_course_group.pk).get()
        self.assertEqual(second_course_group.start_date, first_course_group.start_date,
                         'Second import must be rebased, not left on raw example_schedule.json dates')
        self.assertEqual(second_course_group.end_date, first_course_group.end_date)

    def test_example_schedule_gets_the_4_0_plus_minus_grade_scale_and_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        exampleschedulehelper.given_example_import_allowed(user)

        # WHEN
        response = exampleschedulehelper.post_import_example_schedule(self.client)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        course_group = CourseGroup.objects.get(user=user)
        self.assertEqual(course_group.grade_scale_template, enums.GRADE_SCALE_4_0_PLUS_MINUS)
        self.assertEqual(course_group.grade_scale,
                         enums.GRADE_SCALE_TEMPLATES[enums.GRADE_SCALE_4_0_PLUS_MINUS]['scale'])
        self.assertNotEqual(float(course_group.gpa), -1)
        for course in Course.objects.filter(course_group=course_group):
            self.assertNotEqual(float(course.grade_point), -1, course.title)
