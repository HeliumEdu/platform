__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import re

_TRAILING_NUMBER_PATTERN = re.compile(r'^(.*?)(\d+)$')


def next_clone_title(title):
    """Increment a trailing number on the title, or append ' 1' if none (``"Quiz"`` -> ``"Quiz 1"``; ``"Quiz 9"`` -> ``"Quiz 10"``)."""
    match = _TRAILING_NUMBER_PATTERN.match(title)
    if match:
        prefix, number = match.group(1), int(match.group(2))
        return f'{prefix}{number + 1}'
    return f'{title} 1'
