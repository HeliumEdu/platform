"""
Utility functions.
"""

import requests

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


def get_status_code(url, allow_redirects=False):
    response = requests.head(url, allow_redirects=allow_redirects)

    return response.status_code


def remove_non_alnum(str):
    return unicode(''.join(e for e in str.lower() if e.isalnum()))


def get_page_range(paginator, results):
    start_page_range = results.number - 5 if results.number >= 5 else 0
    end_page_range = results.number + 4 if results.number <= len(paginator.page_range) - 4 else len(
            paginator.page_range)
    page_range = paginator.page_range[start_page_range:end_page_range]
    if paginator.num_pages not in page_range:
        page_range.append('...')
        page_range.append(paginator.num_pages)

    return page_range
