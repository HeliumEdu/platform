__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.planner.models import MaterialGroup

logger = logging.getLogger(__name__)


class MaterialGroupSerializer(serializers.ModelSerializer):
    """
    A bucket of resources, organized free-form (by term, by kind, all in
    one). See
    https://www.heliumedu.com/support/resources/using-resources-to-track-study-materials
    """

    class Meta:
        model = MaterialGroup
        fields = ('id', 'title', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)
