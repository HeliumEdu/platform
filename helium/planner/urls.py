from django.conf.urls import url

from helium.planner.views.apis.attachmentviews import AttachmentsApiListView, AttachmentsApiDetailView
from helium.planner.views.apis.categoryviews import UserCategoriesApiListView, CourseGroupCourseCategoriesApiListView, \
    CourseGroupCourseCategoriesApiDetailView
from helium.planner.views.apis.coursegroupviews import CourseGroupsApiDetailView
from helium.planner.views.apis.coursegroupviews import CourseGroupsApiListView
from helium.planner.views.apis.coursescheduleresourceviews import CourseScheduleAsEventsResourceView
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiDetailView
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiListView
from helium.planner.views.apis.courseviews import CourseGroupCoursesApiDetailView, CourseGroupCoursesApiListView, \
    UserCoursesApiListView
from helium.planner.views.apis.eventviews import EventsApiListView, EventsApiDetailView
from helium.planner.views.apis.graderesourceviews import GradesApiResourceView
from helium.planner.views.apis.homeworkviews import UserHomeworkApiListView, CourseGroupCourseHomeworkApiListView, \
    CourseGroupCourseHomeworkApiDetailView
from helium.planner.views.apis.materialgroupviews import MaterialGroupsApiDetailView
from helium.planner.views.apis.materialgroupviews import MaterialGroupsApiListView
from helium.planner.views.apis.materialviews import MaterialGroupMaterialsApiDetailView, UserMaterialsApiListView, \
    MaterialGroupMaterialsApiListView
from helium.planner.views.apis.reminderviews import RemindersApiListView, RemindersApiDetailView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

urlpatterns = [
    ##############################
    # Authenticated URLs
    ##############################
    # Resource shortcuts
    url(r'^planner/grades/$', GradesApiResourceView.as_view(), name='planner_resource_grades'),
    url(r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/courseschedules/events/$',
        CourseScheduleAsEventsResourceView.as_view(), name='planner_resource_courseschedules_events'),

    # CourseGroup
    url(r'^planner/coursegroups/$', CourseGroupsApiListView.as_view(), name='planner_coursegroups_list'),
    url(r'^planner/coursegroups/(?P<pk>[0-9]+)/$', CourseGroupsApiDetailView.as_view(),
        name='planner_coursegroups_detail'),

    # Course
    url(r'^planner/courses/$', UserCoursesApiListView.as_view(), name='planner_courses_list'),
    url(r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/$', CourseGroupCoursesApiListView.as_view(),
        name='planner_coursegroups_courses_list'),
    url(r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<pk>[0-9]+)/$',
        CourseGroupCoursesApiDetailView.as_view(),
        name='planner_coursegroups_courses_detail'),

    # CourseSchedule
    url(r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/courseschedules/$',
        CourseGroupCourseCourseSchedulesApiListView.as_view(),
        name='planner_coursegroups_courses_courseschedules_list'),
    url(
        r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/courseschedules/(?P<pk>[0-9]+)/$',
        CourseGroupCourseCourseSchedulesApiDetailView.as_view(),
        name='planner_coursegroups_courses_courseschedules_detail'),

    # Category
    url(r'^planner/categories/$', UserCategoriesApiListView.as_view(), name='planner_categories_list'),
    url(r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/categories/$',
        CourseGroupCourseCategoriesApiListView.as_view(),
        name='planner_coursegroups_courses_categories_list'),
    url(
        r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/categories/(?P<pk>[0-9]+)/$',
        CourseGroupCourseCategoriesApiDetailView.as_view(),
        name='planner_coursegroups_courses_categories_detail'),

    # Attachment
    url(r'^planner/attachments/$', AttachmentsApiListView.as_view(), name='planner_attachments_list'),
    url(r'^planner/attachments/(?P<pk>[0-9]+)/$', AttachmentsApiDetailView.as_view(),
        name='planner_attachments_detail'),

    # MaterialGroup
    url(r'^planner/materialgroups/$', MaterialGroupsApiListView.as_view(), name='planner_materialgroups_list'),
    url(r'^planner/materialgroups/(?P<pk>[0-9]+)/$', MaterialGroupsApiDetailView.as_view(),
        name='planner_materialgroups_detail'),

    # Material
    url(r'^planner/materials/$', UserMaterialsApiListView.as_view(), name='planner_materials_list'),
    url(r'^planner/materialgroups/(?P<material_group>[0-9]+)/materials/$',
        MaterialGroupMaterialsApiListView.as_view(),
        name='planner_materialgroups_materials_list'),
    url(r'^planner/materialgroups/(?P<material_group>[0-9]+)/materials/(?P<pk>[0-9]+)/$',
        MaterialGroupMaterialsApiDetailView.as_view(),
        name='planner_materialgroups_materials_detail'),

    # Event
    url(r'^planner/events/$', EventsApiListView.as_view(), name='planner_events_list'),
    url(r'^planner/events/(?P<pk>[0-9]+)/$', EventsApiDetailView.as_view(), name='planner_events_detail'),

    # Homework
    url(r'^planner/homework/$', UserHomeworkApiListView.as_view(), name='planner_homework_list'),
    url(r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/homework/$',
        CourseGroupCourseHomeworkApiListView.as_view(),
        name='planner_coursegroups_courses_homework_list'),
    url(
        r'^planner/coursegroups/(?P<course_group>[0-9]+)/courses/(?P<course>[0-9]+)/homework/(?P<pk>[0-9]+)/$',
        CourseGroupCourseHomeworkApiDetailView.as_view(),
        name='planner_coursegroups_courses_homework_detail'),

    # Reminder
    url(r'^planner/reminders/$', RemindersApiListView.as_view(), name='planner_reminders_list'),
    url(r'^planner/reminders/(?P<pk>[0-9]+)/$', RemindersApiDetailView.as_view(),
        name='planner_reminders_detail'),
]
