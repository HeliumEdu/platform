import datetime
from typing import Iterable, List


def parse_csv_exceptions(csv: str) -> List[datetime.date]:
    """
    Parse a comma-separated YYYYMMDD string into a list of dates. Blank or
    malformed tokens are silently skipped (matches frontend tolerance — invalid
    rows shouldn't crash callers; use the validator for strict checking).

    :param csv: Raw CSV value as stored on ``Course.exceptions`` / ``CourseGroup.exceptions``.
    :return: List of :class:`datetime.date` (input order preserved; not deduplicated).
    """
    if not csv or not csv.strip():
        return []

    result: List[datetime.date] = []
    for token in csv.split(','):
        token = token.strip()
        if len(token) != 8:
            continue
        try:
            result.append(datetime.datetime.strptime(token, '%Y%m%d').date())
        except ValueError:
            continue
    return result


def merge_exceptions(
    course_exceptions: Iterable[datetime.date],
    course_group_exceptions: Iterable[datetime.date],
) -> List[datetime.date]:
    """
    Merge a course's own exception dates with its course group's exception dates
    (semester holidays), returning a deduplicated, sorted list of all dates on
    which the course does not meet.
    """
    seen: set = set()
    merged: List[datetime.date] = []
    for dt in [*course_exceptions, *course_group_exceptions]:
        if dt in seen:
            continue
        seen.add(dt)
        merged.append(dt)
    merged.sort()
    return merged


def get_course_exceptions(course) -> set:
    """
    Return the set of dates on which ``course`` does not meet — the merge of
    course-level (professor cancellations) and course-group-level (holidays,
    breaks) exceptions. Shared by every call site that needs to skip
    non-meeting days when walking a course's schedule (reminders, the ICS
    feed, RRULE generation).

    :param course: A ``Course`` instance with ``exceptions`` and
                   ``course_group.exceptions`` CSV fields.
    """
    return set(merge_exceptions(
        parse_csv_exceptions(course.exceptions),
        parse_csv_exceptions(course.course_group.exceptions),
    ))
