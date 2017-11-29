"""
Form for user settings modification.
"""

from helium.common.forms.base import BaseForm
from helium.users.models import UserSetting

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserSettingForm(BaseForm):
    class Meta:
        model = UserSetting
        fields = ('time_zone',)
