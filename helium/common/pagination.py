__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger(__name__)


class DefaultPageNumberPagination(PageNumberPagination):
    """Returns a bare list unless the client passes ``page``/``page_size``."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        opted_in = (
            self.page_query_param in request.query_params
            or self.page_size_query_param in request.query_params
        )
        if not opted_in:
            return None

        return super().paginate_queryset(queryset, request, view=view)
