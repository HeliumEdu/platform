__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from rest_framework import serializers

from helium.planner.models import MaterialGroup

logger = logging.getLogger(__name__)


class MaterialGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialGroup
        fields = ('id', 'title', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)
