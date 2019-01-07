import logging

from rest_framework import serializers

from helium.planner.models import MaterialGroup

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class MaterialGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialGroup
        fields = ('id', 'title', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)
