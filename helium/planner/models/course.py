
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from helium.common import enums
from helium.common.errormessages import EXCEPTION_DATES_OUTSIDE_CLASS_MESSAGE
from helium.common.models import BaseModel
from helium.common.utils.commonutils import random_color
from helium.common.utils.validators import validate_and_normalize_date_csv, validate_hex_color
from helium.planner.managers.coursemanager import CourseManager


class Course(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255)

    room = models.CharField(help_text='An arbitrary string.',
                            max_length=255, blank=True, default='')

    credits = models.DecimalField(
        help_text='A decimal corresponding to credit hours, weighting the course in its group\'s `gpa`. If unknown or '
                  'the syllabus doesn\'t specify, use `"0.00"`.',
        max_digits=4, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(99)])

    color = models.CharField(
        help_text='A valid hex color code choice to determine the color events will be shown on the calendar.',
        max_length=7, validators=[validate_hex_color], default=random_color)

    website = models.URLField(help_text='A valid URL.', max_length=3000, blank=True, null=True)

    is_online = models.BooleanField(
        help_text='Whether the course is online.',
        default=False)

    current_grade = models.DecimalField(max_digits=7, default=enums.NO_GRADE, decimal_places=4)

    grade_point = models.DecimalField(
        help_text="The grade point `current_grade` earns on the course's grade scale (`grade_scale_template`, else "
                  "the group's `grade_scale`), or `-1` when ungraded or the group has no grade scale.",
        max_digits=5, default=enums.NO_GRADE, decimal_places=2)

    grade_scale_template = models.PositiveSmallIntegerField(
        help_text="A preset grade scale for this course, when its syllabus grades differently from its group: one whose "
                  "grades (grade point and label) the group's `grade_scale` also awards. Null to use the group's "
                  "`grade_scale`.",
        choices=enums.COURSE_GRADE_SCALE_TEMPLATE_CHOICES, default=None, blank=True, null=True)

    trend = models.FloatField(default=None, blank=True, null=True)

    teacher_name = models.CharField(help_text='A display name for the teacher.',
                                    max_length=255, blank=True, default='')

    teacher_email = models.EmailField(help_text='A valid email address.',
                                      max_length=254, blank=True, default='')

    start_date = models.DateField(help_text='ISO-8601 date. Must be on-or-before `end_date`.')
    end_date = models.DateField(help_text='ISO-8601 date. Must be on-or-after `start_date`.')

    course_group = models.ForeignKey('CourseGroup', help_text='The course group with which to associate.',
                                     related_name='courses', on_delete=models.CASCADE)

    exceptions = models.TextField(
        help_text='Comma-separated dates (YYYYMMDD) when this course does not meet.',
        blank=True, default='')

    objects = CourseManager()

    class Meta:
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        ordering = ('start_date', 'title')

    def clean(self):
        super().clean()
        if self.exceptions:
            self.exceptions = validate_and_normalize_date_csv(
                self.exceptions, self.start_date, self.end_date,
                out_of_range_message=EXCEPTION_DATES_OUTSIDE_CLASS_MESSAGE)

    def __str__(self):  # pragma: no cover
        return str(f'{self.title} ({self.get_user().get_username()})')

    def get_user(self):
        return self.course_group.get_user()

    @property
    def has_weighted_grading(self) -> bool:
        return Course.objects.has_weighted_grading(self.pk)

    @property
    def num_homework(self) -> int:
        return self.homework.count()

    @property
    def num_homework_completed(self) -> int:
        return self.homework.completed().count()

    @property
    def num_homework_graded(self) -> int:
        return self.homework.graded().count()

    @property
    def num_reminders(self) -> int:
        return self.reminders.count()

    @property
    def num_attachments(self):
        return self.attachments.count()
