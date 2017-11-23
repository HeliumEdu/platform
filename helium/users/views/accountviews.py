"""
Account view entrance functions.
"""

import logging

import pytz
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from statsd.defaults.django import statsd

from helium.users.forms.userpasswordform import UserPasswordForm
from helium.users.services import authservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


@login_required
def account_settings(request):
    if authservice.is_anonymous_or_non_admin(request.user):
        statsd.incr('platform.view.settings')

    return render(request, "account/settings.html")
