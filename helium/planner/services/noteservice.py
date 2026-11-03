import logging

from helium.planner.models import Event, Homework, Resource
from helium.planner.serializers.noteserializer import NoteSerializer

logger = logging.getLogger(__name__)

_LINK_FIELD_BY_MODEL = {Homework: 'homework', Event: 'events', Resource: 'resources'}


def create_linked_note(content, user, item, *, example_schedule=False, context=None):
    """
    Create an untitled Note holding `content`, linked to `item`.

    :param content: The Quill Delta the Note holds.
    :param user: The Note's owner.
    :param item: The Homework, Event or Resource the Note is linked to.
    :param example_schedule: Whether the Note is part of the example schedule.
    :param context: Serializer context; pass the request to scope the link to its user's rows.
    :return: The created Note.
    :raises ValidationError: If the Note is invalid, e.g. `item` already has a linked Note.
    """
    serializer = NoteSerializer(
        data={'title': '', 'content': content, _LINK_FIELD_BY_MODEL[type(item)]: [item.pk]},
        context=context or {})
    serializer.is_valid(raise_exception=True)

    return serializer.save(user=user, example_schedule=example_schedule)
