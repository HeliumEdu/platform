
from django.conf import settings
from django.db import models

from helium.common import enums
from helium.common.models import BaseModel
from helium.common.utils.gradeutils import default_grade_scale, preset_for
from helium.common.utils.validators import validate_and_normalize_date_csv
from helium.planner.managers.coursegroupmanager import CourseGroupManager


class CourseGroup(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255)

    start_date = models.DateField(help_text='ISO-8601 date. Must be on-or-before `end_date`.')

    end_date = models.DateField(help_text='ISO-8601 date. Must be on-or-after `start_date`.')

    shown_on_calendar = models.BooleanField(help_text='Whether items should be shown on the calendar.',
                                            default=True)

    overall_grade = models.DecimalField(max_digits=7, default=enums.NO_GRADE, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    grade_scale = models.JSONField(
        help_text='The bands that map a class grade to a grade point, or empty for no grade scale.',
        default=default_grade_scale)

    grade_scale_template = models.PositiveSmallIntegerField(
        help_text='The preset `grade_scale` matches, or null for a custom scale.',
        choices=enums.GRADE_SCALE_TEMPLATE_CHOICES, default=enums.GRADE_SCALE_NONE, blank=True, null=True)

    gpa = models.DecimalField(
        help_text="The credit-weighted mean of the classes' `grade_point`, or `-1` with no grade scale or no graded "
                  "class with credits.",
        max_digits=7, default=enums.NO_GRADE, decimal_places=4)

    example_schedule = models.BooleanField(help_text='Whether it is part of the example schedule.',
                                           default=False)

    exceptions = models.TextField(
        help_text='Comma-separated dates (YYYYMMDD) when no classes occur (holidays, breaks).',
        blank=True, default='')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='course_groups', on_delete=models.CASCADE)

    objects = CourseGroupManager()

    class Meta:
        verbose_name = 'Class group'
        ordering = ('start_date', 'title')

    def clean(self):
        super().clean()
        if self.exceptions:
            self.exceptions = validate_and_normalize_date_csv(
                self.exceptions, self.start_date, self.end_date, range_label='group date range')

    def save(self, *args, **kwargs):
        self.grade_scale_template = preset_for(self.grade_scale)
        super().save(*args, **kwargs)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.user

    @property
    def num_courses(self) -> int:
        return self.courses.count()

    @property
    def num_homework(self) -> int:
        return self.courses.num_homework()

    @property
    def num_homework_completed(self) -> int:
        return self.courses.num_homework_completed()

    @property
    def num_homework_graded(self) -> int:
        return self.courses.num_homework_graded()

    @property
    def num_attachments(self):
        return self.courses.num_attachments()
