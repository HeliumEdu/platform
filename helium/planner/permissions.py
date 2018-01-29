import logging

from rest_framework import permissions
from rest_framework.exceptions import NotFound

from helium.planner.models import Course, CourseGroup, MaterialGroup, Event, Homework, Category, Material

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class IsCourseGroupOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if 'course_group' not in view.kwargs:
            return False

        check_course_group_permission(request.user.pk, view.kwargs['course_group'])

        return True


class IsCourseOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if 'course' not in view.kwargs:
            return False

        check_course_permission(request.user.pk, view.kwargs['course'])

        return True


class IsMaterialGroupOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if 'material_group' not in view.kwargs:
            return False

        check_material_group_permission(request.user.pk, view.kwargs['material_group'])

        return True


def check_course_group_permission(user_id, course_group_id):
    if not CourseGroup.objects.exists_for_user(course_group_id, user_id):
        raise NotFound('CourseGroup not found.')


def check_course_permission(user_id, course_id):
    if not Course.objects.exists_for_user(course_id, user_id):
        raise NotFound('Course not found.')


def check_material_group_permission(user_id, material_group_id):
    if not MaterialGroup.objects.exists_for_user(material_group_id, user_id):
        raise NotFound('MaterialGroup not found.')


def check_event_permission(user_id, event_id):
    if not Event.objects.exists_for_user(event_id, user_id):
        raise NotFound('Event not found.')


def check_homework_permission(user_id, homework_id):
    if not Homework.objects.exists_for_user(homework_id, user_id):
        raise NotFound('Homework not found.')


def check_category_permission(user_id, category_id):
    if not Category.objects.exists_for_user(category_id, user_id):
        raise NotFound('Category not found.')


def check_material_permission(user_id, material_id):
    if not Material.objects.exists_for_user(material_id, user_id):
        raise NotFound('Material not found.')
