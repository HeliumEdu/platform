__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from django import forms


class UserDeleteForm(forms.Form):
    username = forms.CharField()

    email = forms.CharField()

    password = forms.CharField()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if self.user.email != email:
            raise forms.ValidationError("The given email does not match.")

        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not self.user.check_password(password):
            raise forms.ValidationError("Your password was entered incorrectly.")

        return password
