__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum

from helium.common.models import BaseModel
from helium.common.utils.commonutils import random_color
from helium.common.utils.validators import validate_hex_color
from helium.planner.managers.categorymanager import CategoryManager


class Category(BaseModel):
    title = models.CharField(help_text='A display name. Must be unique within the parent course.',
                             max_length=255)

    weight = models.DecimalField(
        help_text=(
            'Decimal in `[0, 100]`. Sum across a class\'s categories must be <= 100. '
            'A weight of `0` is organizational only when at least one category in the class has '
            '`weight > 0` (weighted mode); when no category has a non-zero weight, the class is '
            'points-based and every assignment contributes via its `current_grade` fraction '
            'regardless of category weight. '
            'See `Course.has_weighted_grading` and '
            'https://heliumedu.freshdesk.com/support/solutions/articles/159000418648'
        ),
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])

    color = models.CharField(
        help_text='A valid hex color code choice to determine the color items will be shown on the calendar.',
        max_length=7, validators=[validate_hex_color], default=random_color)

    average_grade = models.DecimalField(max_digits=7, default=-1, decimal_places=4)

    grade_by_weight = models.DecimalField(max_digits=7, default=0, decimal_places=4)

    trend = models.FloatField(default=None, blank=True, null=True)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='categories', on_delete=models.CASCADE)

    objects = CategoryManager()

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = (
            ('course', 'title'),
        )
        ordering = ('title',)

    def clean(self):
        super().clean()
        if self.weight is not None and self.course_id:
            qs = Category.objects.filter(course_id=self.course_id)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            sibling_total = qs.aggregate(Sum('weight'))['weight__sum'] or 0
            if sibling_total + self.weight > 100:
                raise ValidationError({
                    'weight': 'The cumulative weights of all categories associated with a course cannot exceed 100%.'
                })

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.course.course_group.get_user()

    @property
    def num_homework(self) -> int:
        return self.homework.count()

    @property
    def num_homework_completed(self) -> int:
        return self.homework.completed().count()

    @property
    def num_homework_graded(self) -> int:
        return self.homework.graded().count()
