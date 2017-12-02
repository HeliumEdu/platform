"""
Form for user password modification.
"""
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.forms import BaseForm

from helium.users.utils.userutils import validate_password

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserPasswordForm(PasswordChangeForm, BaseForm):
    def clean_new_password2(self):
        """
        Check the password meets the validation criteria.
        """
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")

        error = validate_password(password1, password2)

        if error:
            raise forms.ValidationError(error)

        return password2
