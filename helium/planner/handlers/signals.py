__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from helium.common import enums
from helium.common.utils import taskutils
from helium.planner.models import Category, Course, CourseGroup, Event, Homework, CourseSchedule, Attachment, Material
from helium.planner.services import coursescheduleservice
from helium.planner.tasks import recalculate_category_grades_for_course, recalculate_category_grade, \
    adjust_reminder_times, recalculate_course_grades_for_course_group, recalculate_course_grade

logger = logging.getLogger(__name__)


def _mark_user_data_deleted(instance):
    try:
        user = instance.get_user()
        user.settings.last_deletion_at = timezone.now()
        user.settings.save(update_fields=['last_deletion_at'])
    except Exception:
        logger.warning("Failed to update last_deletion_at after delete.", exc_info=True)


@receiver(post_save, sender=Course)
def save_course(sender, instance, **kwargs):
    coursescheduleservice.clear_cached_course_schedule(instance)
    taskutils.safe_apply_async(recalculate_course_grade, args=(instance.pk,), priority=settings.CELERY_PRIORITY_LOW)
    taskutils.safe_apply_async(adjust_reminder_times, args=(instance.pk, enums.COURSE), priority=settings.CELERY_PRIORITY_LOW)


@receiver(post_delete, sender=Course)
def delete_course(sender, instance, **kwargs):
    _mark_user_data_deleted(instance)
    taskutils.safe_apply_async(recalculate_course_grades_for_course_group,
        args=(instance.course_group.pk,), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_save, sender=CourseSchedule)
def save_course_schedule(sender, instance, **kwargs):
    coursescheduleservice.clear_cached_course_schedule(instance.course)
    taskutils.safe_apply_async(adjust_reminder_times,
        args=(instance.course.pk, enums.COURSE), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_save, sender=Category)
def save_category(sender, instance, **kwargs):
    taskutils.safe_apply_async(recalculate_category_grade, args=(instance.pk,), priority=settings.CELERY_PRIORITY_LOW)


@receiver(post_delete, sender=Category)
def delete_category(sender, instance, **kwargs):
    _mark_user_data_deleted(instance)
    taskutils.safe_apply_async(recalculate_category_grades_for_course,
        args=(instance.course.pk,), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_delete, sender=Homework)
def delete_homework(sender, instance, **kwargs):
    _mark_user_data_deleted(instance)
    try:
        if instance.category:
            taskutils.safe_apply_async(recalculate_category_grade,
                args=(instance.category.pk,), priority=settings.CELERY_PRIORITY_LOW
            )
    except Category.DoesNotExist:
        logger.info(f"Category does not exist for Homework {instance.pk}. Nothing to do.")


@receiver(post_save, sender=Event)
def save_event(sender, instance, **kwargs):
    taskutils.safe_apply_async(adjust_reminder_times,
        args=(instance.pk, instance.calendar_item_type), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_save, sender=Homework)
def save_homework(sender, instance, **kwargs):
    if instance.category:
        taskutils.safe_apply_async(recalculate_category_grade,
            args=(instance.category.pk,), priority=settings.CELERY_PRIORITY_LOW
        )

    taskutils.safe_apply_async(adjust_reminder_times,
        args=(instance.pk, instance.calendar_item_type), priority=settings.CELERY_PRIORITY_LOW
    )


@receiver(post_delete, sender=Attachment)
def delete_attachment(sender, instance, **kwargs):
    """
    Delete the associated file in storage, if it exists.
    """
    if instance.attachment:
        instance.attachment.delete(False)


@receiver(pre_delete, sender=Homework)
def delete_homework_children(sender, instance, **kwargs):
    """Explicitly delete Homework's children before the outer Collector reaches its
    field_updates step. Attachment and Reminder both carry a three-FK exactly_one_parent
    CHECK constraint; on MySQL (no deferrable constraints) Django's CASCADE for nullable
    FKs emits UPDATE homework_id=NULL before DELETE, which transiently leaves all three
    parent columns NULL and violates the CHECK. Deleting them here zero-rows that UPDATE.
    Notes use the same pattern for N+1 avoidance.
    """
    instance.notes_set.all().delete()
    instance.attachments.all().delete()
    instance.reminders.all().delete()


@receiver(pre_delete, sender=Event)
def delete_event_children(sender, instance, **kwargs):
    """Explicitly delete Event's children before the outer Collector reaches its
    field_updates step — see delete_homework_children for the full rationale.
    """
    instance.notes_set.all().delete()
    instance.attachments.all().delete()
    instance.reminders.all().delete()


@receiver(pre_delete, sender=Material)
def delete_material_notes(sender, instance, **kwargs):
    """Delete linked Notes when a Material is deleted.

    Uses bulk delete to avoid N+1 queries. Note: bulk delete doesn't trigger
    Note's pre_delete signal, but that's OK since the linked entity (this
    Material) is being deleted anyway.
    """
    instance.notes_set.all().delete()


@receiver(pre_delete, sender=Course)
def delete_course_children(sender, instance, **kwargs):
    """Explicitly delete Course's direct Attachment and Reminder children before the outer
    Collector reaches its field_updates step — see delete_homework_children for the full
    rationale. Homework-owned children are handled by delete_homework_children when the
    Homework cascade itself fires.
    """
    instance.attachments.all().delete()
    instance.reminders.all().delete()


@receiver(post_delete, sender=Event)
def delete_event(sender, instance, **kwargs):
    _mark_user_data_deleted(instance)


@receiver(post_delete, sender=CourseSchedule)
def delete_course_schedule(sender, instance, **kwargs):
    _mark_user_data_deleted(instance)


@receiver(post_delete, sender=CourseGroup)
def delete_course_group(sender, instance, **kwargs):
    _mark_user_data_deleted(instance)
