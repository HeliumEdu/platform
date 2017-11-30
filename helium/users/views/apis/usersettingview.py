"""
Authenticated views for user setting modification.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View

from helium.users.forms.usersettingform import UserSettingForm

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class UserSettingView(View):
    def get(self, request):
        user_setting_form = UserSettingForm(instance=request.user.settings)

        return HttpResponse(user_setting_form)
