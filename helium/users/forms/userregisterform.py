"""
Form for user registration.
"""

from django import forms
from django.contrib.auth import get_user_model

from helium.common import enums
from helium.common.forms.base import BaseForm
from helium.users.utils.userutils import validate_password

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserRegisterForm(forms.ModelForm, BaseForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)
    time_zone = forms.ChoiceField(label='Time zone', choices=enums.TIME_ZONE_CHOICES)

    class Meta:
        model = get_user_model()
        fields = ['email', 'username']

    def clean_password2(self):
        """
        Check the password meets the validation criteria.
        """
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        error = validate_password(password1, password2)

        if error:
            raise forms.ValidationError(error)

        return password2

    def save(self, commit=True):
        """
        Save the provided password in hashed format.

        If commit is not set to True, time_zone will also not be saved (as it requires a persisted user object).

        :param commit: If True, changes to the instance will be saved to the database.
        """
        user = super(UserRegisterForm, self).save(commit=False)
        user.set_password(self.cleaned_data.get("password1"))

        if commit:
            user.save()

            # On registration, the user's time zone is also provided; now that the user is created, it's dependent models
            # have also been created, so save it to the user's settings
            user.settings.time_zone = self.cleaned_data.get("time_zone")
            user.settings.save()

        return user
