import logging
from datetime import datetime
from typing import Iterator, List, NamedTuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import router, transaction
from django.db.models import Model, Q, QuerySet
from django.db.models.deletion import Collector
from django.utils import timezone

from helium.auth.models import UserSettings
from helium.feed.models import ExternalCalendar
from helium.planner.models import Course, CourseGroup, Event, Homework, Material, MaterialGroup, Note, Reminder

logger = logging.getLogger(__name__)

#: Every model that carries the example schedule flag.
FLAGGED_MODELS = (ExternalCalendar, CourseGroup, MaterialGroup, Event, Note)


class ExamplePartition(NamedTuple):
    """
    The user's example schedule roots, split by whether the user has changed anything under them.
    """

    #: Roots with nothing authored by the user beneath them, safe to delete.
    pristine: List[Model]
    #: Roots with anything created or changed by the user beneath them, which must be kept.
    modified: List[Model]
    #: Untouched courses inside a kept group, safe to delete while the group and the user's courses stay.
    pristine_children: List[Model]


def partition_example_schedule(user_id: int) -> ExamplePartition:
    """
    Split the user's example schedule roots into those that are untouched and those the user has changed.

    A root is every flagged top-level example entity. Everything the database would cascade-delete with it is
    inspected, so a row the user added anywhere beneath a root keeps that root. Within a kept course group, each
    course is judged on its own, so only the courses the user touched are kept alongside it. Without an import
    stamp nothing can be proven untouched, so every root is kept.

    :param user_id: The user whose example schedule to inspect.
    :return: The pristine roots, the modified roots, and the untouched courses within the modified groups.
    """
    stamp = get_user_model().objects.filter(pk=user_id).values_list('example_schedule_imported_at',
                                                                    flat=True).first()

    if stamp is None:
        roots = list(_example_roots(user_id))
        if roots:
            logger.warning(f'User {user_id} has no example schedule import stamp, keeping all {len(roots)} roots')
        return ExamplePartition(pristine=[], modified=roots, pristine_children=[])

    pristine = []
    modified = []
    pristine_children = []
    for root in _example_roots(user_id):
        if not _is_modified(root, stamp):
            pristine.append(root)
            continue

        modified.append(root)
        if isinstance(root, CourseGroup):
            pristine_children.extend(course for course in Course.objects.filter(course_group=root)
                                     if not _is_modified(course, stamp))

    return ExamplePartition(pristine=pristine, modified=modified, pristine_children=pristine_children)


def promote(roots: List[Model]) -> None:
    """
    Hand the given roots, and everything beneath them, over to the user by unflagging them.

    Uses a queryset update so the roots' own modification time is untouched.

    :param roots: The roots to stop treating as example data.
    """
    for root in roots:
        type(root).objects.filter(pk=root.pk).update(example_schedule=False)
        _linked_notes(list(_cascade_instances(root))).filter(example_schedule=True).update(example_schedule=False)
        logger.info(f'Promoted example schedule {type(root).__name__} {root.pk} to user data')


def promote_modified(user_id: int) -> None:
    """
    Promote every example schedule root the user has changed, leaving untouched ones flagged.

    :param user_id: The user whose example schedule to inspect.
    """
    promote(partition_example_schedule(user_id).modified)


def adopt(user_id: int) -> None:
    """
    Make the user's whole example schedule their own: unflag every example entity and stop the Getting Started
    dialog. Nothing is deleted.

    :param user_id: The user whose example schedule to adopt.
    """
    with transaction.atomic():
        UserSettings.objects.select_for_update().filter(user_id=user_id).first()

        adopted = sum(model.objects.filter(user_id=user_id, example_schedule=True).update(example_schedule=False)
                      for model in FLAGGED_MODELS)
        (UserSettings.objects
         .filter(user_id=user_id, show_getting_started=True)
         .update(show_getting_started=False, updated_at=timezone.now()))

    logger.info(f'Adopted the example schedule for user {user_id} ({adopted} entities)')


def adopt_stale(now: datetime = None) -> int:
    """
    Adopt the example schedule for every user who imported it more than EXAMPLE_SCHEDULE_ADOPTION_DAYS ago and
    still has any of it flagged.

    :param now: The current time, for tests.
    :return: The number of users adopted.
    """
    cutoff = (now or timezone.now()) - settings.EXAMPLE_SCHEDULE_ADOPTION_AGE
    stale_user_ids = set(get_user_model().objects
                         .filter(example_schedule_imported_at__lte=cutoff)
                         .values_list('pk', flat=True))
    flagged_user_ids = set()
    for model in FLAGGED_MODELS:
        flagged_user_ids.update(model.objects
                                .filter(example_schedule=True, user_id__in=stale_user_ids)
                                .values_list('user_id', flat=True))

    for user_id in flagged_user_ids:
        adopt(user_id)

    return len(flagged_user_ids)


def _example_roots(user_id: int) -> Iterator[Model]:
    yield from ExternalCalendar.objects.for_user(user_id).filter(example_schedule=True)
    yield from CourseGroup.objects.for_user(user_id).filter(example_schedule=True)
    yield from MaterialGroup.objects.for_user(user_id).filter(example_schedule=True)
    yield from Event.objects.for_user(user_id).filter(example_schedule=True)
    yield from Note.objects.for_user(user_id).filter(example_schedule=True, homework__isnull=True,
                                                     events__isnull=True, resources__isnull=True)


def _is_modified(root: Model, baseline: datetime) -> bool:
    cascade = list(_cascade_instances(root))

    if any(_changed_after(instance, baseline) for instance in cascade):
        return True

    return _linked_notes(cascade).filter(updated_at__gt=baseline).exists()


def _cascade_instances(root: Model) -> Iterator[Model]:
    collector = Collector(using=router.db_for_write(type(root)))
    collector.collect([root])

    for instances in collector.data.values():
        yield from instances
    for queryset in collector.fast_deletes:
        yield from queryset


def _changed_after(instance: Model, baseline: datetime) -> bool:
    # Background jobs re-save reminders and create each repeating course reminder's successor when one fires, so a
    # reminder's timestamps say nothing about the user. Only the item a reminder belongs to counts as edited.
    if isinstance(instance, Reminder):
        return False

    updated_at = getattr(instance, 'updated_at', None)

    return updated_at is not None and updated_at > baseline


def _linked_notes(cascade: List[Model]) -> QuerySet:
    # Deleting a Homework, Event or Material deletes its linked notes from a pre_delete signal handler, which the
    # collector cannot see, so they are looked up separately.
    homework_ids = [i.pk for i in cascade if isinstance(i, Homework)]
    event_ids = [i.pk for i in cascade if isinstance(i, Event)]
    material_ids = [i.pk for i in cascade if isinstance(i, Material)]

    return Note.objects.filter(
        Q(homework__in=homework_ids) | Q(events__in=event_ids) | Q(resources__in=material_ids))
