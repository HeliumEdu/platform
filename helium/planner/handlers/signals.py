__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from helium.planner.models import Category, Course, Event, Homework, CourseSchedule, Attachment
from helium.planner.services import coursescheduleservice
from helium.planner.tasks import recalculate_category_grades_for_course, recalculate_category_grade, \
    adjust_reminder_times, recalculate_course_grades_for_course_group, recalculate_course_grade

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Course)
def save_course(sender, instance, **kwargs):
    coursescheduleservice.clear_cached_course_schedule(instance)
    recalculate_course_grade.apply_async(args=(instance.pk,), priority=settings.CELERY_PRIORITY_LOW)


@receiver(post_delete, sender=Course)
def delete_course(sender, instance, **kwargs):
    recalculate_course_grades_for_course_group.apply_async(
        args=(instance.course_group.pk,), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_save, sender=CourseSchedule)
def save_course_schedule(sender, instance, **kwargs):
    coursescheduleservice.clear_cached_course_schedule(instance.course)


@receiver(post_save, sender=Category)
def save_category(sender, instance, **kwargs):
    recalculate_category_grade.apply_async(args=(instance.pk,), priority=settings.CELERY_PRIORITY_LOW)


@receiver(post_delete, sender=Category)
def delete_category(sender, instance, **kwargs):
    recalculate_category_grades_for_course.apply_async(
        args=(instance.course.pk,), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_delete, sender=Homework)
def delete_homework(sender, instance, **kwargs):
    try:
        if instance.category:
            recalculate_category_grade.apply_async(
                args=(instance.category.pk,), priority=settings.CELERY_PRIORITY_LOW
            )
    except Category.DoesNotExist:
        logger.info(f"Category does not exist for Homework {instance.pk}. Nothing to do.")


@receiver(post_save, sender=Event)
def save_event(sender, instance, **kwargs):
    adjust_reminder_times.apply_async(
        args=(instance.pk, instance.calendar_item_type), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_save, sender=Homework)
def save_homework(sender, instance, **kwargs):
    if instance.category:
        recalculate_category_grade.apply_async(
            args=(instance.category.pk,), priority=settings.CELERY_PRIORITY_LOW
        )

    adjust_reminder_times.apply_async(
        args=(instance.pk, instance.calendar_item_type), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_delete, sender=Attachment)
def delete_attachment(sender, instance, **kwargs):
    """
    Delete the associated file in storage, if it exists.
    """
    if instance.attachment:
        instance.attachment.delete(False)
