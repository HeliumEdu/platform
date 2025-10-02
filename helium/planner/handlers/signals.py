__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from helium.planner.models import Category, Course, Event, Homework, CourseSchedule, Attachment
from helium.planner.services import coursescheduleservice
from helium.planner.tasks import recalculate_category_grades_for_course, recalculate_category_grade, \
    adjust_reminder_times, recalculate_course_group_grade

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Course)
def save_course(sender, instance, **kwargs):
    coursescheduleservice.clear_cached_course_schedule(instance)


@receiver(post_delete, sender=Course)
def delete_course(sender, instance, **kwargs):
    recalculate_course_group_grade.delay(instance.course_group.pk)


@receiver(post_save, sender=CourseSchedule)
def save_course_schedule(sender, instance, **kwargs):
    coursescheduleservice.clear_cached_course_schedule(instance.course)


@receiver(post_save, sender=Category)
def save_category(sender, instance, **kwargs):
    recalculate_category_grade.delay(instance.pk)


@receiver(post_delete, sender=Category)
def delete_category(sender, instance, **kwargs):
    recalculate_category_grades_for_course.delay(instance.course.pk)


@receiver(post_delete, sender=Homework)
def delete_homework(sender, instance, **kwargs):
    try:
        if instance.category:
            recalculate_category_grade.delay(instance.category.pk)
    except Category.DoesNotExist:
        logger.info(f"Category does not exist for Homework {instance.pk}. Nothing to do.")


@receiver(post_save, sender=Event)
def save_event(sender, instance, **kwargs):
    adjust_reminder_times.delay(instance.pk, instance.calendar_item_type)


@receiver(post_save, sender=Homework)
def save_homework(sender, instance, **kwargs):
    if instance.category:
        recalculate_category_grade.delay(instance.category.pk)

    adjust_reminder_times.delay(instance.pk, instance.calendar_item_type)


@receiver(post_delete, sender=Attachment)
def delete_attachment(sender, instance, **kwargs):
    """
    Delete the associated file in storage, if it exists.
    """
    if instance.attachment:
        instance.attachment.delete(False)
