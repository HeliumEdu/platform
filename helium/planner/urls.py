"""
Planner URLs.
"""

from django.conf.urls import url
from django.views.generic import RedirectView

from helium.planner.views.apis.coursegroupview import CourseGroupsApiDetailView
from helium.planner.views.apis.coursegroupview import CourseGroupsApiLCView
from helium.planner.views.apis.courseview import CourseGroupCoursesApiDetailView, CourseGroupCoursesApiLCView, \
    UserCoursesApiListView
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
    url(r'^api/planner/coursegroups/$', CourseGroupsApiLCView.as_view(), name='api_planner_coursegroups_lc'),
    url(r'^api/planner/coursegroups/(?P<pk>[0-9]+)/$', CourseGroupsApiDetailView.as_view(),
        name='api_planner_coursegroups_detail'),

    url(r'^api/planner/courses/$', UserCoursesApiListView.as_view(), name='api_planner_courses_list'),
    url(r'^api/planner/coursegroups/(?P<course_group_id>[0-9]+)/courses/$', CourseGroupCoursesApiLCView.as_view(),
        name='api_planner_coursegroups_courses_lc'),
    url(r'^api/planner/coursegroups/(?P<course_group_id>[0-9]+)/courses/(?P<pk>[0-9]+)/$',
        CourseGroupCoursesApiDetailView.as_view(),
        name='api_planner_coursegroups_courses_detail'),
]
