"""
Base attributes from which all other Planner models should derive.
"""

import logging
from abc import abstractmethod

from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class BasePlannerModel(BaseModel):
    class Meta:
        abstract = True

    @abstractmethod
    def get_user(self):
        pass
