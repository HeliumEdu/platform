import datetime

from django.core import validators
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.common.models import BaseModel
from helium.planner.managers.coursemanager import CourseManager

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.1'


@python_2_unicode_compatible
class Course(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    room = models.CharField(help_text='An arbitrary string.',
                            max_length=255, blank=True)

    credits = models.DecimalField(help_text='A decimal corresponding to credit hours.',
                                  max_digits=4, decimal_places=2)

    color = models.CharField(
        help_text='A valid hex color code choice to determine the color events will be shown on the calendar',
        max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    website = models.URLField(help_text='A valid URL.', max_length=3000, blank=True, null=True)

    is_online = models.BooleanField(
        help_text='Whether or not the course is online (and thus may have times associated with it)',
        default=False)

    current_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    private_slug = models.SlugField(unique=True, blank=True, null=True)

    # TODO: teacher details will be abstracted into a Teacher model after the open source migration is finished
    teacher_name = models.CharField(help_text='A display name for the teacher.',
                                    max_length=255, blank=True)

    teacher_email = models.EmailField(help_text='A valid email address.',
                                      default=None, blank=True, null=True)

    # TODO: these fields will be abstracted into a CourseSchedule model after the open source migration is finished
    start_date = models.DateField(help_text='An ISO-8601 date.')
    end_date = models.DateField(help_text='An ISO-8601 date.')
    days_of_week = models.CharField(help_text='Seven booleans (0 or 1) indicating which days of the week the course is '
                                              'on (week starts on Sunday).',
                                    max_length=7, default='0000000', validators=[
            validators.RegexValidator(r'^[0-1]+$',
                                      'Seven booleans (0 or 1) indicating which days of the week the course is on (week '
                                      'starts on Sunday).',
                                      'invalid'),
            validators.MinLengthValidator(7,
                                          'Seven booleans (0 or 1) indicating which days of the week the course is on '
                                          '(week starts on Sunday).')])
    sun_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    sun_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    mon_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    mon_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    tue_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    tue_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    wed_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    wed_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    thu_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    thu_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    fri_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    fri_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    sat_start_time = models.TimeField(help_text='An ISO-8601 time.',
                                      default=datetime.time(12, 0, 0))
    sat_end_time = models.TimeField(help_text='An ISO-8601 time.',
                                    default=datetime.time(12, 0, 0))
    # TODO: when CourseSchedule is created, it should simply be a foreign key relationship so "_alt" is no longer needed and any number of alt schedules can exist
    days_of_week_alt = models.CharField(help_text='Seven booleans (0 or 1) indicating which days of the week the '
                                                  'course is on (week starts on Sunday).',
                                        max_length=7, default='0000000', validators=[
            validators.RegexValidator(r'^[0-1]+$',
                                      'Seven booleans (0 or 1) indicating which days of the week the course is on (week '
                                      'starts on Sunday).',
                                      'invalid'),
            validators.MinLengthValidator(7,
                                          'Seven booleans (0 or 1) indicating which days of the week the course is on '
                                          '(week starts on Sunday).')])
    sun_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    sun_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))
    mon_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    mon_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))
    tue_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    tue_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))
    wed_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    wed_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))
    thu_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    thu_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))
    fri_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    fri_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))
    sat_start_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                          default=datetime.time(12, 0, 0))
    sat_end_time_alt = models.TimeField(help_text='An ISO-8601 time.',
                                        default=datetime.time(12, 0, 0))

    course_group = models.ForeignKey('CourseGroup', help_text='The course group with which to associate.',
                                     related_name='courses', on_delete=models.CASCADE)

    objects = CourseManager()

    class Meta:
        ordering = ('start_date',)

    def __str__(self):  # pragma: no cover
        return str('{} ({})'.format(self.title, self.get_user().get_username()))

    def get_user(self):
        return self.course_group.get_user()

    @property
    def has_weighted_grading(self):
        return Course.objects.has_weighted_grading(self.pk)

    @property
    def num_items(self):
        return self.homework.count()

    @property
    def num_complete(self):
        return self.homework.completed().count()

    @property
    def num_incomplete(self):
        return self.homework.completed().count()

    @property
    def num_graded(self):
        return self.homework.graded().count()
