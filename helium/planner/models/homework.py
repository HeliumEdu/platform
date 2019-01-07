from django.db import models

from helium.common import enums
from helium.common.utils.validators import validate_fraction
from helium.planner.managers.homeworkmanager import HomeworkManager
from helium.planner.models import Category
from helium.planner.models.basecalendar import BaseCalendar

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"


class Homework(BaseCalendar):
    current_grade = models.CharField(help_text='The current grade in fraction form (ex. 25/30).',
                                     max_length=255, validators=[validate_fraction])

    completed = models.BooleanField(help_text='Whether or not the homework has been completed.',
                                    default=False)

    category = models.ForeignKey('Category', help_text='The category with which to associate.',
                                 related_name='homework', blank=True, null=True, default=None,
                                 on_delete=models.SET_NULL)

    materials = models.ManyToManyField('Material', help_text='A list of materials with which to associate.',
                                       related_name='homework', blank=True, default=None)

    course = models.ForeignKey('Course', help_text='The course with which to associate.',
                               related_name='homework', on_delete=models.CASCADE)

    objects = HomeworkManager()

    class Meta:
        verbose_name_plural = 'Homework'
        ordering = ('start', 'title')

    def get_user(self):
        return self.course.get_user()

    @property
    def calendar_item_type(self):
        return enums.HOMEWORK

    def save(self, *args, **kwargs):
        """
        Saves the current instance.

        If `category` is None, the field will instead be set to the default "Uncategorized" category for the given
        course.

        Saving the instance will also invoke grade recalculation for related fields. If the `category` has been changed,
        category grade recalculation for the previously linked category should be invoked manually before executing this
        method, as this method will only recalculate the grade for the category to which the field is being changed.
        """
        if not self.category:
            self.category = Category.objects.get_uncategorized(self.course_id)

        super().save(*args, **kwargs)
