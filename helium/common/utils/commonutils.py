"""
Common utility functions.
"""

from random import choice

from django.conf import settings

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def generate_random_color(used=()):
    color = choice(settings.ALLOWED_COLORS)
    # Once we've used all allowed colors, we have to duplicate, but until then try to be unique
    if len(used) < len(settings.ALLOWED_COLORS):
        while color in used:
            color = choice(settings.ALLOWED_COLORS)
    return color
