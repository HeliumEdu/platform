"""
Form for user settings modification.
"""
from django import forms

from helium.common.forms.base import BaseForm
from helium.users.models import UserSetting

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserSettingForm(forms.ModelForm, BaseForm):
    class Meta:
        model = UserSetting
        fields = ('default_view', 'week_starts_on', 'show_getting_started', 'default_reminder_offset',
                  'default_reminder_offset_type', 'default_reminder_type', 'time_zone',)
