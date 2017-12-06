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
def recalculate_course_group_grade(self, course_group):
    # TODO: not yet implemented
    pass
