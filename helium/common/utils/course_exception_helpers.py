__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

"""
Backend helpers for the YYYYMMDD-CSV exception format used by
``Course.exceptions`` and ``CourseGroup.exceptions``. Mirrors the frontend
``CourseExceptionHelpers`` (`lib/utils/course_exception_helpers.dart`) so
parsing, formatting, and merging behave identically on both sides.

These are the loose "give me dates" / "give me a CSV" primitives. For
end-to-end validation (range check, normalization, error surfaces) use
:func:`helium.common.utils.validators.validate_and_normalize_date_csv`.
"""

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
