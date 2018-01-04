import logging

from rest_framework import serializers

from helium.planner.models import Homework

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class HomeworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'comments', 'current_grade',
            'completed', 'course', 'category', 'materials')
        read_only_fields = ('calendar_item_type', 'user',)
