from django.conf import settings


def note_url(notes_set) -> str:
    """
    The deep link to the first note in ``notes_set``, or an empty string when there is no note
    with content.

    :param notes_set: A related manager of notes.
    :return: The note's URL, or ``''``.
    """
    notes = list(notes_set.all())
    if notes and notes[0].content:
        return f'{settings.PROJECT_APP_HOST}/notebook/{notes[0].pk}'
    return ''
