"""
Abstract model for Base form.
"""

from django import forms

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')

        super(BaseForm, self).__init__(*args, **kwargs)

    class Meta:
        abstract = True
