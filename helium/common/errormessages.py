import math

from django.conf import settings
from django.utils.translation import gettext, gettext_lazy, ngettext

EMAIL_IN_USE_MESSAGE = gettext_lazy("That email is already in use. Try signing in instead.")

EXCEPTION_DATES_OUT_OF_RANGE_MESSAGE = gettext_lazy('Exception dates must fall within the date range.')
EXCEPTION_DATES_OUTSIDE_CLASS_MESSAGE = gettext_lazy('Exception dates must fall within the class date range.')
EXCEPTION_DATES_OUTSIDE_GROUP_MESSAGE = gettext_lazy('Exception dates must fall within the group date range.')
EXCEPTION_DATES_OUTSIDE_SCHEDULE_MESSAGE = gettext_lazy('Exception dates must fall within the schedule date range.')

REGISTRATION_RETRY_MESSAGE = gettext_lazy("Please wait a moment and try again.")

RESET_LINK_INVALID_MESSAGE = gettext_lazy('This reset link is invalid or has expired. Please request a new one.')

SIGN_IN_TO_CONTINUE_MESSAGE = gettext_lazy('Please sign in to continue.')

VERIFICATION_CODE_INVALID_MESSAGE = gettext_lazy("That code doesn't look right. Please check and try again.")


def admin_allowed_email_error() -> str:
    """
    The message shown when an admin email falls outside ADMIN_ALLOWED_DOMAINS.
    """
    return gettext('Admin email must be within an allowed domain (%(domains)s).') % {
        'domains': ', '.join(settings.ADMIN_ALLOWED_DOMAINS)}


def attachment_type_not_allowed_message(name) -> str:
    return gettext('Attachment "%(name)s" file type is not allowed.') % {'name': name}


def category_title_duplicate_message(title) -> str:
    return gettext('This class already has a category named "%(title)s".') % {'title': title}


def not_an_occurrence_message(model) -> str:
    return {
        'event': gettext('Not an occurrence of this event.'),
        'homework': gettext('Not an occurrence of this assignment.'),
    }[model._meta.model_name]


def not_found_message(model) -> str:
    return {
        'course': gettext('Class not found.'),
        'coursegroup': gettext('Group not found.'),
        'resource': gettext('Resource not found.'),
        'resourcegroup': gettext('Group not found.'),
    }.get(model._meta.model_name, gettext('Item not found.'))


def not_repeating_message(model) -> str:
    return {
        'event': gettext("This event doesn't repeat."),
        'homework': gettext("This assignment doesn't repeat."),
    }[model._meta.model_name]


def oauth_sign_in_failed_message(provider_name) -> str:
    return gettext('Sign in with %(provider)s failed. Please try again.') % {'provider': provider_name}


def throttled_message(wait) -> str:
    if wait is None:
        return gettext('Too many attempts. Try again later.')

    minutes = math.ceil(int(wait) / 60)
    if minutes <= 1:
        return gettext('Too many attempts. Try again in a minute.')
    if minutes < 60:
        return ngettext('Too many attempts. Try again in %(count)s minute.',
                        'Too many attempts. Try again in %(count)s minutes.', minutes) % {'count': minutes}

    hours = (minutes + 30) // 60
    if hours == 1:
        return gettext('Too many attempts. Try again in about an hour.')
    return ngettext('Too many attempts. Try again in about %(count)s hour.',
                    'Too many attempts. Try again in about %(count)s hours.', hours) % {'count': hours}


def titled_message(title, error) -> str:
    return gettext('"%(title)s": %(error)s') % {'title': title, 'error': error}
