import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from helium.planner.models import Category, Course, Homework
from helium.planner.tasks import recalculate_course_group_grade, recalculate_course_grade, recalculate_category_grade

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Course)
def delete_course(sender, instance, **kwargs):
    recalculate_course_group_grade.delay(instance.course_group.pk)


@receiver(post_save, sender=Category)
def save_category(sender, instance, **kwargs):
    recalculate_category_grade.delay(instance.pk)


@receiver(post_delete, sender=Category)
def delete_category(sender, instance, **kwargs):
    recalculate_course_grade.delay(instance.course.pk)


@receiver(post_delete, sender=Homework)
def delete_homework(sender, instance, **kwargs):
    try:
        if instance.category:
            recalculate_category_grade.delay(instance.category.pk)
    except Category.DoesNotExist:
        pass


@receiver(post_save, sender=Homework)
def save_homework(sender, instance, **kwargs):
    if instance.category:
        recalculate_category_grade.delay(instance.category.pk)
