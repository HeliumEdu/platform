import logging

from conf.celery import app
from helium.common.utils import metricutils
from helium.planner.services import gradingservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def recalculate_course_group_grade(course_group):
    metricutils.increment('task.grading.recalculate.course-group')

    gradingservice.recalculate_course_group_grade(course_group)


@app.task
def recalculate_course_grade(course):
    metricutils.increment('task.grading.recalculate.course')

    gradingservice.recalculate_course_grade(course)

    recalculate_course_group_grade.delay(course.course_group)


@app.task
def recalculate_category_grade(category):
    metricutils.increment('task.grading.recalculate.category')

    gradingservice.recalculate_category_grade(category)

    recalculate_course_grade.delay(category.course)
