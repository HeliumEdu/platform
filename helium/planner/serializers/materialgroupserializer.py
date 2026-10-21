import logging

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.common.utils.openapiutils import support_article_url
from helium.planner.models import MaterialGroup

logger = logging.getLogger(__name__)


#: Once all backend code has been factored from Material terminology to Resource terminology, including data model changes and migrations, this line can be removed.
@extend_schema_serializer(component_name='ResourceGroup', description=(
    'A bucket of resources, organized free-form (by term, by kind, all in one). See '
    f"{support_article_url('notebook/using-resources-to-track-study-materials')}"
))
class MaterialGroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = MaterialGroup
        fields = ('id', 'title', 'shown_on_calendar', 'user', 'created_at', 'updated_at',)
        read_only_fields = ('user', 'created_at', 'updated_at',)
