"""
Planner URLs.
"""

from django.conf.urls import url
from django.views.generic import RedirectView

from helium.planner.views.pages import calendar, classes, materials, grades

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

urlpatterns = [
    # Base URL
    url(r'^$', RedirectView.as_view(pattern_name='calendar', permanent=True), name='planner'),

    # Planner URLs
    url(r'^calendar/$', calendar, name='calendar'),
    url(r'^classes/$', classes, name='classes'),
    url(r'^materials/$', materials, name='materials'),
    url(r'^grades/$', grades, name='grades'),
]
