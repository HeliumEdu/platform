"""
Context processors defining attributes that will be passed to all templates.
"""

from django.conf import settings

from helium.planner.services import reminderservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def template(request):
    reminders_count = 0
    if hasattr(request, 'user') and request.user.is_authenticated():
        reminders_count = reminderservice.find_by_user(request.user)

    context = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'PROJECT_TAGLINE': settings.PROJECT_TAGLINE,
        'PROJECT_VERSION': settings.PROJECT_VERSION,
        'PROJECT_EMAIL': settings.EMAIL_ADDRESS,
        'REMINDERS_COUNT': reminders_count,
    }
    return context
