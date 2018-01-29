import logging

from conf.celery import app
from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course, Category
from helium.planner.services import gradingservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def recalculate_course_group_grade(course_group_id):
    metricutils.increment('task.grading.recalculate.course-group')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        gradingservice.recalculate_course_group_grade(CourseGroup.objects.get(pk=course_group_id))
    except Category.DoesNotExist:
        pass


@app.task
def recalculate_course_grade(course_id):
    metricutils.increment('task.grading.recalculate.course')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course = Course.objects.get(pk=course_id)

        gradingservice.recalculate_course_grade(course)

        recalculate_course_group_grade.delay(course.course_group.pk)
    except Course.DoesNotExist:
        pass


@app.task
def recalculate_category_grade(category_id):
    metricutils.increment('task.grading.recalculate.category')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        category = Category.objects.get(pk=category_id)

        gradingservice.recalculate_category_grade(category)

        recalculate_course_grade.delay(category.course.pk)
    except Category.DoesNotExist:
        pass
