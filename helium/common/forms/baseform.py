from django import forms

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class BaseForm(forms.BaseForm):
    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)

        for field in list(self.fields.values()):
            field.widget.attrs['placeholder'] = field.label

    class Meta:
        abstract = True
