__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.planner.models import MaterialGroup

logger = logging.getLogger(__name__)


class MaterialGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialGroup
        fields = ('id', 'title', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)
