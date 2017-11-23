"""
Form for user password modification.
"""

from django.contrib.admin import forms
from django.forms import BaseForm

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


class UserPasswordForm(forms.PasswordChangeForm, BaseForm):
    pass
