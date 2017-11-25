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
