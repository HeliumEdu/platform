"""
Form for user's personal information modification.
"""

from helium.common.forms.base import BaseForm
from helium.users.models import UserSetting

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserProfileForm(BaseForm):
    class Meta:
        model = UserSetting
        fields = ('address_1', 'address_2', 'city', 'state', 'postal_code',)
