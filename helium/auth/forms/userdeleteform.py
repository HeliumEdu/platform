from django import forms

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserDeleteForm(forms.Form):
    username = forms.CharField()

    email = forms.CharField()

    password = forms.CharField()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserDeleteForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not self.user.check_password(password):
            raise forms.ValidationError("Your password was entered incorrectly.")

        return password
