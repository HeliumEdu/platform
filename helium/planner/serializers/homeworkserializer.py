import logging

from rest_framework import serializers

from helium.planner.models import Homework
from helium.planner.tasks import gradingtasks

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

    def update(self, instance, validated_data):
        old_category = self.instance.category if self.instance.category_id != validated_data['category'] else None

        instance = super(HomeworkSerializer, self).update(instance, validated_data)

        if old_category:
            gradingtasks.recalculate_category_grade(old_category)

        return instance
