"""
Planner URLs.
"""

from django.conf.urls import url
from django.views.generic import RedirectView

from helium.planner.views.apis.attachmentviews import UserAttachmentsApiListView, AttachmentsApiDetailView, \
    CourseAttachmentsApiListView
from helium.planner.views.apis.categoryviews import UserCategoriesApiListView, CourseGroupCourseCategoriesApiListView, \
    CourseGroupCourseCategoriesApiDetailView
from helium.planner.views.apis.coursegroupviews import CourseGroupsApiDetailView
from helium.planner.views.apis.coursegroupviews import CourseGroupsApiListView
from helium.planner.views.apis.courseviews import CourseGroupCoursesApiDetailView, CourseGroupCoursesApiListView, \
    UserCoursesApiListView
from helium.planner.views.apis.materialgroupviews import MaterialGroupsApiDetailView
from helium.planner.views.apis.materialgroupviews import MaterialGroupsApiListView
from helium.planner.views.apis.materialviews import MaterialGroupMaterialsApiDetailView, UserMaterialsApiListView, \
    MaterialGroupMaterialsApiListView
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

    ##############################
    # Authenticated API URLs
    ##############################
    # CourseGroup
    url(r'^api/planner/coursegroups/$', CourseGroupsApiListView.as_view(), name='api_planner_coursegroups_list'),
    url(r'^api/planner/coursegroups/(?P<pk>[0-9]+)/$', CourseGroupsApiDetailView.as_view(),
        name='api_planner_coursegroups_detail'),

    # Course
    url(r'^api/planner/courses/$', UserCoursesApiListView.as_view(), name='api_planner_courses_list'),
    url(r'^api/planner/coursegroups/(?P<course_group_id>[0-9]+)/courses/$', CourseGroupCoursesApiListView.as_view(),
        name='api_planner_coursegroups_courses_list'),
    url(r'^api/planner/coursegroups/(?P<course_group_id>[0-9]+)/courses/(?P<pk>[0-9]+)/$',
        CourseGroupCoursesApiDetailView.as_view(),
        name='api_planner_coursegroups_courses_detail'),

    # Category
    url(r'^api/planner/categories/$', UserCategoriesApiListView.as_view(), name='api_planner_categories_list'),
    url(r'^api/planner/coursegroups/(?P<course_group_id>[0-9]+)/courses/(?P<course_id>[0-9]+)/categories/$',
        CourseGroupCourseCategoriesApiListView.as_view(),
        name='api_planner_coursegroups_courses_categories_list'),
    url(
        r'^api/planner/coursegroups/(?P<course_group_id>[0-9]+)/courses/(?P<course_id>[0-9]+)/categories/(?P<pk>[0-9]+)/$',
        CourseGroupCourseCategoriesApiDetailView.as_view(),
        name='api_planner_coursegroups_courses_categories_detail'),

    # Attachment
    url(r'^api/planner/courses/(?P<course_id>[0-9]+)/attachments/$', CourseAttachmentsApiListView.as_view(),
        name='api_planner_courses_attachments_list'),
    url(r'^api/planner/attachments/$', UserAttachmentsApiListView.as_view(), name='api_planner_attachments_list'),
    url(r'^api/planner/attachments/(?P<pk>[0-9]+)/$', AttachmentsApiDetailView.as_view(),
        name='api_planner_attachments_detail'),

    # MaterialGroup
    url(r'^api/planner/materialgroups/$', MaterialGroupsApiListView.as_view(), name='api_planner_materialgroups_list'),
    url(r'^api/planner/materialgroups/(?P<pk>[0-9]+)/$', MaterialGroupsApiDetailView.as_view(),
        name='api_planner_materialgroups_detail'),

    # Material
    url(r'^api/planner/materials/$', UserMaterialsApiListView.as_view(), name='api_planner_materials_list'),
    url(r'^api/planner/materialgroups/(?P<material_group_id>[0-9]+)/materials/$',
        MaterialGroupMaterialsApiListView.as_view(),
        name='api_planner_materialgroups_materials_list'),
    url(r'^api/planner/materialgroups/(?P<material_group_id>[0-9]+)/materials/(?P<pk>[0-9]+)/$',
        MaterialGroupMaterialsApiDetailView.as_view(),
        name='api_planner_materialgroups_materials_detail'),
]
