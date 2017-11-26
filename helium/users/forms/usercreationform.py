"""
Form for user creation.
"""

from django import forms
from django.contrib.auth import get_user_model

from helium.common.forms.base import BaseForm
from helium.common.utils import is_password_valid

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


class UserCreationForm(BaseForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)

    class Meta:
        """
        Define metadata for this model.
        """

        model = get_user_model()
        fields = ['email', 'username', 'time_zone']

    def clean_password2(self):
        """
        Check that the two password entries match.
        """
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("You must enter matching passwords.")
            elif not is_password_valid(password1):
                raise forms.ValidationError(
                    "Your password must be at least 8 characters long and contain one letter and one number.")

        return password2

    def save(self, commit=True):
        """
        Save the provided password in hashed format.

        :param commit: If True, changes to the instance will be saved to the database.
        """
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data.get("password1"))

        if commit:
            user.save()

        return user
