__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from helium.planner.models import Category, Course, Event, Homework, CourseSchedule, Attachment, Note, NoteLink
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


# Track notes being deleted to prevent signal recursion
_notes_being_deleted = set()


@receiver(pre_delete, sender=Note)
def delete_note(sender, instance, **kwargs):
    """
    Clear the linked entity's notes field when a Note is deleted.

    This ensures dual-write consistency: if a user deletes a Note via the API,
    the linked entity's inline notes field is also cleared.
    """
    _notes_being_deleted.add(instance.pk)
    for link in instance.links.select_related('homework', 'event', 'resource').all():
        entity = link.linked_entity
        if entity and hasattr(entity, 'notes'):
            entity.notes = None
            entity.save(update_fields=['notes', 'updated_at'])


@receiver(post_delete, sender=Note)
def cleanup_note_deletion_tracking(sender, instance, **kwargs):
    """Clean up tracking set after note deletion completes."""
    _notes_being_deleted.discard(instance.pk)


@receiver(pre_delete, sender=NoteLink)
def delete_notelink(sender, instance, **kwargs):
    """
    Delete the associated Note when a NoteLink is deleted.

    This ensures that when an entity (Homework, Event, Material) is deleted,
    the cascade to NoteLink also cascades to the Note itself.

    Skips deletion if the Note is already being deleted (e.g., cascade from Note.delete()).
    """
    try:
        note_id = instance.note_id
        logger.info(f"NoteLink {instance.pk} pre_delete signal: note_id={note_id}, "
                    f"linked_entity_type={instance.linked_entity_type}")
        if note_id and note_id not in _notes_being_deleted:
            _notes_being_deleted.add(note_id)
            logger.info(f"Deleting Note {note_id} due to NoteLink cascade")
            instance.note.delete()
        elif note_id in _notes_being_deleted:
            logger.info(f"Note {note_id} already being deleted, skipping cascade")
    except Note.DoesNotExist:
        logger.info(f"Note {note_id} does not exist, nothing to cascade")
