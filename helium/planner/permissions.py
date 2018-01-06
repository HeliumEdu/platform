import logging

from rest_framework.exceptions import NotFound

from helium.planner.models import Course, CourseGroup, MaterialGroup, Event, Homework, Category, Material

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


# TODO: as these have now be generified, they can all be abstracted out into proper Permissions classes that implement check_object_permissions
def check_course_permission(request, course_id):
    if not Course.objects.exists_for_user(course_id, request.user.pk):
        raise NotFound('Course not found.')


def check_material_group_permission(request, material_group_id):
    if not MaterialGroup.objects.exists_for_user(material_group_id, request.user.pk):
        raise NotFound('MaterialGroup not found.')


def check_course_group_permission(request, course_group_id):
    if not CourseGroup.objects.exists_for_user(course_group_id, request.user.pk):
        raise NotFound('CourseGroup not found.')


def check_event_permission(request, event_id):
    if not Event.objects.exists_for_user(event_id, request.user.pk):
        raise NotFound('Event not found.')


def check_homework_permission(request, homework_id):
    if not Homework.objects.exists_for_user(homework_id, request.user.pk):
        raise NotFound('Homework not found.')


def check_category_permission(request, category_id):
    if not Category.objects.exists_for_user(category_id, request.user.pk):
        raise NotFound('Category not found.')


def check_material_permission(request, material_id):
    if not Material.objects.exists_for_user(material_id, request.user.pk):
        raise NotFound('Material not found.')
