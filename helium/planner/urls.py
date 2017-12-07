"""
Planner URLs.
"""

from django.conf.urls import url
from django.views.generic import RedirectView

from helium.planner.views.apis.coursegroupview import CourseGroupsApiDetailView
from helium.planner.views.apis.coursegroupview import CourseGroupsApiListView
from helium.planner.views.generalviews import calendar, classes, materials, grades

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

urlpatterns = [
    # Base URL
    url(r'^planner/$', RedirectView.as_view(pattern_name='calendar', permanent=True), name='planner'),

    # Planner URLs
    url(r'^planner/calendar', calendar, name='calendar'),
    url(r'^planner/classes', classes, name='classes'),
    url(r'^planner/materials', materials, name='materials'),
    url(r'^planner/grades', grades, name='grades'),

    # Authenticated API URLs
    url(r'^api/planner/coursegroups/$', CourseGroupsApiListView.as_view(), name='api_planner_coursegroups_list'),
    url(r'^api/planner/coursegroups/(?P<pk>[0-9]+)/$', CourseGroupsApiDetailView.as_view(),
        name='api_planner_coursegroups_detail'),
]
