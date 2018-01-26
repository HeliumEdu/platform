import logging
from abc import abstractmethod

from django.db import models

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @abstractmethod
    def get_user(self):
        """
        Returns the User that owns this model. Note that not all models necessarily have a direct reference to the User,
        so calling this function may indirectly query for user details.

        :return: The User with ownership of this model.
        """
        raise NotImplementedError
