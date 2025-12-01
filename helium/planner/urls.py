__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.42"

from django.urls import path

from helium.planner.views.apis.attachmentviews import AttachmentsApiListView, AttachmentsApiDetailView
from helium.planner.views.apis.categoryviews import UserCategoriesApiListView, CourseGroupCourseCategoriesApiListView, \
    CourseGroupCourseCategoriesApiDetailView
from helium.planner.views.apis.coursegroupviews import CourseGroupsApiDetailView
from helium.planner.views.apis.coursegroupviews import CourseGroupsApiListView
from helium.planner.views.apis.coursescheduleaseventsviews import CourseScheduleAsEventsListView, \
    UserCourseScheduleAsEventsListView
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiDetailView
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiListView
from helium.planner.views.apis.courseviews import CourseGroupCoursesApiDetailView, CourseGroupCoursesApiListView, \
    UserCoursesApiListView
from helium.planner.views.apis.eventviews import EventsApiListView, EventsApiDetailView, EventsApiDeleteResourceView
from helium.planner.views.apis.graderesourceviews import GradesApiResourceView
from helium.planner.views.apis.homeworkviews import UserHomeworkApiListView, CourseGroupCourseHomeworkApiListView, \
    CourseGroupCourseHomeworkApiDetailView
from helium.planner.views.apis.materialgroupviews import MaterialGroupsApiDetailView
from helium.planner.views.apis.materialgroupviews import MaterialGroupsApiListView
from helium.planner.views.apis.materialviews import MaterialGroupMaterialsApiDetailView, UserMaterialsApiListView, \
    MaterialGroupMaterialsApiListView
from helium.planner.views.apis.reminderviews import RemindersApiListView, RemindersApiDetailView

urlpatterns = [
    ##############################
    # Authenticated URLs
    ##############################
    # Resource shortcuts
    path('planner/grades/', GradesApiResourceView.as_view(), name='planner_resource_grades'),
    path('planner/coursegroups/<int:course_group>/courses/<int:course>/courseschedules/events/',
         CourseScheduleAsEventsListView.as_view(), name='planner_resource_courses_courseschedules_events'),
    path('planner/courseschedules/events/', UserCourseScheduleAsEventsListView.as_view(),
         name='planner_courseschedules_events'),

    # CourseGroup
    path('planner/coursegroups/', CourseGroupsApiListView.as_view(), name='planner_coursegroups_list'),
    path('planner/coursegroups/<int:pk>/', CourseGroupsApiDetailView.as_view(),
         name='planner_coursegroups_detail'),

    # Course
    path('planner/courses/', UserCoursesApiListView.as_view(), name='planner_courses_list'),
    path('planner/coursegroups/<int:course_group>/courses/', CourseGroupCoursesApiListView.as_view(),
         name='planner_coursegroups_courses_list'),
    path('planner/coursegroups/<int:course_group>/courses/<int:pk>/',
         CourseGroupCoursesApiDetailView.as_view(),
         name='planner_coursegroups_courses_detail'),

    # CourseSchedule
    path('planner/coursegroups/<int:course_group>/courses/<int:course>/courseschedules/',
         CourseGroupCourseCourseSchedulesApiListView.as_view(),
         name='planner_coursegroups_courses_courseschedules_list'),
    path(
        'planner/coursegroups/<int:course_group>/courses/<int:course>/courseschedules/<int:pk>/',
        CourseGroupCourseCourseSchedulesApiDetailView.as_view(),
        name='planner_coursegroups_courses_courseschedules_detail'),

    # Category
    path('planner/categories/', UserCategoriesApiListView.as_view(), name='planner_categories_list'),
    path('planner/coursegroups/<int:course_group>/courses/<int:course>/categories/',
         CourseGroupCourseCategoriesApiListView.as_view(),
         name='planner_coursegroups_courses_categories_list'),
    path(
        'planner/coursegroups/<int:course_group>/courses/<int:course>/categories/<int:pk>/',
        CourseGroupCourseCategoriesApiDetailView.as_view(),
        name='planner_coursegroups_courses_categories_detail'),

    # Attachment
    path('planner/attachments/', AttachmentsApiListView.as_view(), name='planner_attachments_list'),
    path('planner/attachments/<int:pk>/', AttachmentsApiDetailView.as_view(),
         name='planner_attachments_detail'),

    # MaterialGroup
    path('planner/materialgroups/', MaterialGroupsApiListView.as_view(), name='planner_materialgroups_list'),
    path('planner/materialgroups/<int:pk>/', MaterialGroupsApiDetailView.as_view(),
         name='planner_materialgroups_detail'),

    # Material
    path('planner/materials/', UserMaterialsApiListView.as_view(), name='planner_materials_list'),
    path('planner/materialgroups/<int:material_group>/materials/',
         MaterialGroupMaterialsApiListView.as_view(),
         name='planner_materialgroups_materials_list'),
    path('planner/materialgroups/<int:material_group>/materials/<int:pk>/',
         MaterialGroupMaterialsApiDetailView.as_view(),
         name='planner_materialgroups_materials_detail'),

    # Event
    path('planner/events/', EventsApiListView.as_view(), name='planner_events_list'),
    path('planner/events/<int:pk>/', EventsApiDetailView.as_view(), name='planner_events_detail'),
    path('planner/events/delete/all/', EventsApiDeleteResourceView.as_view({'delete': 'delete_all'}),
         name='planner_events_resource_delete'),

    # Homework
    path('planner/homework/', UserHomeworkApiListView.as_view(), name='planner_homework_list'),
    path('planner/coursegroups/<int:course_group>/courses/<int:course>/homework/',
         CourseGroupCourseHomeworkApiListView.as_view(),
         name='planner_coursegroups_courses_homework_list'),
    path(
        'planner/coursegroups/<int:course_group>/courses/<int:course>/homework/<int:pk>/',
        CourseGroupCourseHomeworkApiDetailView.as_view(),
        name='planner_coursegroups_courses_homework_detail'),

    # Reminder
    path('planner/reminders/', RemindersApiListView.as_view(), name='planner_reminders_list'),
    path('planner/reminders/<int:pk>/', RemindersApiDetailView.as_view(),
         name='planner_reminders_detail'),
]
