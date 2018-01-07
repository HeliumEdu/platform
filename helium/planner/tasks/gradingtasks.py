import logging

from conf.celery import app
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def recalculate_course_group_grade(course_group):
    metricutils.increment('task.grading.recalculate.course-group')

    # TODO: not yet implemented


@app.task
def recalculate_course_grade(course):
    metricutils.increment('task.grading.recalculate.course')

    # TODO: not yet implemented

    recalculate_course_group_grade.delay(course.course_group)


@app.task
def recalculate_category_grade(category):
    metricutils.increment('task.grading.recalculate.category')

    # TODO: not yet implemented

    recalculate_course_grade.delay(category.course)
