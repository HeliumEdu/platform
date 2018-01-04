import logging

from rest_framework.exceptions import NotFound

from helium.planner.models import Course, CourseGroup, MaterialGroup, Event, Homework, Category, Material

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def check_course_permission(request, course_id):
    if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
        raise NotFound('Course not found.')


def check_material_group_permission(request, material_group_id):
    if not MaterialGroup.objects.filter(pk=material_group_id, user_id=request.user.pk).exists():
        raise NotFound('MaterialGroup not found.')


def check_course_group_permission(request, course_group_id):
    if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
        raise NotFound('CourseGroup not found.')


def check_event_permission(request, event_id):
    if not Event.objects.filter(pk=event_id, user_id=request.user.pk).exists():
        raise NotFound('Event not found.')


def check_homework_permission(request, homework_id):
    if not Homework.objects.filter(pk=homework_id, course__course_group__user_id=request.user.pk).exists():
        raise NotFound('Homework not found.')


def check_category_permission(request, category_id):
    if not Category.objects.filter(pk=category_id, course__course_group__user_id=request.user.pk).exists():
        raise NotFound('Category not found.')


def check_material_permission(request, material_id):
    if not Material.objects.filter(pk=material_id, material_group__user_id=request.user.pk).exists():
        raise NotFound('Material not found.')
