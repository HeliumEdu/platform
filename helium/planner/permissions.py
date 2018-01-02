import logging

from rest_framework.exceptions import NotFound

from helium.planner.models import Course, CourseGroup, MaterialGroup

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
    raise NotImplementedError
    # TODO: uncomment and when these models exist
    # if not Event.objects.filter(pk=event_id, user_id=request.user.pk).exists():
    #     raise NotFound('Event not found.')


def check_homework_permission(request, homework_id):
    raise NotImplementedError
    # TODO: uncomment and when these models exist
    # if not Homework.objects.filter(pk=homework_id, course__course_group__user_id=request.user.pk).exists():
    #     raise NotFound('Homework not found.')
