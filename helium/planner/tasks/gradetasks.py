"""
Asynchronous grading tasks to be performed.
"""

import logging

from conf.celery import app

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def recalculate_course_group_grade(course_group):
    # TODO: not yet implemented
    pass


@app.task
def recalculate_course_grade(course):
    # TODO: not yet implemented
    pass


@app.task
def recalculate_category_grade(category):
    # TODO: not yet implemented
    pass
