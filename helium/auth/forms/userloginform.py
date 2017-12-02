"""
Form for user registration.
"""

from django import forms

from helium.common.forms.base import BaseForm

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserLoginForm(forms.Form, BaseForm):
    username = forms.CharField(label='Username')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
