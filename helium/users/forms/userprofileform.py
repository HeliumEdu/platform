"""
Form for user profile modification.
"""

from django import forms

from helium.common.forms.base import BaseForm
from helium.users.models import UserProfile

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserProfileForm(forms.ModelForm, BaseForm):
    class Meta:
        model = UserProfile
        fields = ('phone',)
