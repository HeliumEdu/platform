"""
Context processors for project-specific attributes to be passed to templates.
"""

from django.conf import settings

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


def template(request):
    context = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'PROJECT_TAGLINE': settings.PROJECT_TAGLINE,
        'PROJECT_VERSION': settings.PROJECT_VERSION,
        'PROJECT_EMAIL': settings.EMAIL_ADDRESS,
    }
    return context
