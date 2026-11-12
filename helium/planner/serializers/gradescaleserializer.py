import logging

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from helium.common.utils.validators import validate_grade_scale

logger = logging.getLogger(__name__)


class GradeScaleBandSerializer(serializers.Serializer):
    min_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100, coerce_to_string=False,
        help_text='The lowest class grade percentage in this band.')
    grade_point = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100, coerce_to_string=False,
        help_text='The grade point a class grade in this band earns.')
    label = serializers.CharField(
        max_length=10, allow_blank=True, required=False, default='',
        help_text='A display name for the band, e.g. `"A-"`; may be blank.')


@extend_schema_field(GradeScaleBandSerializer(many=True))
class GradeScaleField(serializers.JSONField):
    def to_internal_value(self, data):
        bands = GradeScaleBandSerializer(data=data, many=True)
        bands.is_valid(raise_exception=True)

        grade_scale = [{'min_grade': float(band['min_grade']),
                        'grade_point': float(band['grade_point']),
                        'label': band['label'].strip()}
                       for band in bands.validated_data]
        validate_grade_scale(grade_scale)

        return grade_scale
