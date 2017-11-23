"""
Planner URLs.
"""

from django.conf.urls import url

from helium.planner.views.pages import planner

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

urlpatterns = [
    # Planner URLs
    url(r'^planner', planner, name='planner'),
]
