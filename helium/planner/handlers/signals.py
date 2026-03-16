__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from helium.planner.models import Category, Course, Event, Homework, CourseSchedule, Attachment, Note, Material
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


@receiver(pre_delete, sender=Note)
def delete_note(sender, instance, **kwargs):
    """
    Clear the linked entity's notes field when a Note is deleted.

    This ensures dual-write consistency: if a user deletes a Note via the API,
    the linked entity's inline notes field is also cleared.

    Uses bulk_update to avoid N+1 queries.
    """
    from django.utils import timezone
    now = timezone.now()

    # Clear notes field on all linked homework using bulk update
    homework_list = list(instance.homework.all())
    if homework_list:
        for hw in homework_list:
            hw.notes = None
            hw.updated_at = now
        Homework.objects.bulk_update(homework_list, ['notes', 'updated_at'])

    # Clear notes field on all linked events using bulk update
    events_list = list(instance.events.all())
    if events_list:
        for event in events_list:
            event.notes = None
            event.updated_at = now
        Event.objects.bulk_update(events_list, ['notes', 'updated_at'])

    # Clear notes field on all linked resources using bulk update
    resources_list = list(instance.resources.all())
    if resources_list:
        for resource in resources_list:
            resource.notes = None
            resource.updated_at = now
        Material.objects.bulk_update(resources_list, ['notes', 'updated_at'])


@receiver(pre_delete, sender=Homework)
def delete_homework_notes(sender, instance, **kwargs):
    """Delete linked Notes when a Homework is deleted.

    Uses bulk delete to avoid N+1 queries. Note: bulk delete doesn't trigger
    Note's pre_delete signal, but that's OK since the linked entity (this
    Homework) is being deleted anyway.
    """
    instance.notes_set.all().delete()


@receiver(pre_delete, sender=Event)
def delete_event_notes(sender, instance, **kwargs):
    """Delete linked Notes when an Event is deleted.

    Uses bulk delete to avoid N+1 queries. Note: bulk delete doesn't trigger
    Note's pre_delete signal, but that's OK since the linked entity (this
    Event) is being deleted anyway.
    """
    instance.notes_set.all().delete()


@receiver(pre_delete, sender=Material)
def delete_material_notes(sender, instance, **kwargs):
    """Delete linked Notes when a Material is deleted.

    Uses bulk delete to avoid N+1 queries. Note: bulk delete doesn't trigger
    Note's pre_delete signal, but that's OK since the linked entity (this
    Material) is being deleted anyway.
    """
    instance.notes_set.all().delete()
