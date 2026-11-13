from urllib.parse import quote


def occurrence_query(occurrence_start, scope='this'):
    if not isinstance(occurrence_start, str):
        occurrence_start = occurrence_start.isoformat()
    query = f'occurrence_start={quote(occurrence_start)}'

    return f'scope={scope}&{query}' if scope else query
