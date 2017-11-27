"""
Form for user modification.
"""

from django.contrib.auth import get_user_model

from helium.common.forms.base import BaseForm

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserAddressForm(BaseForm):
    class Meta:
        model = get_user_model()
        fields = ('address_1', 'address_2', 'city', 'state', 'postal_code')
