from django.db.models import QuerySet
from rest_framework import filters

from helium.common.utils.searchutils import matches_search_terms, tokenize_search_query


class HeliumSearchFilter(filters.SearchFilter):
    """
    `?search=` with the same term semantics as the app's own search fields (`searchutils`),
    installed as a default filter backend. A view opts in by declaring `search_fields`, each an
    attribute path on the item (`course__title`), and may set `search_description` for the docs.
    Matching happens in Python over the already-filtered items rather than in SQL, so a view can
    hand it a queryset or a list of in-memory items alike.
    """

    def get_search_terms(self, request):
        return tokenize_search_query(request.query_params.get(self.search_param, ''))

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        terms = self.get_search_terms(request)
        if not search_fields or not terms:
            return queryset

        matching = [item for item in queryset if self._matches(item, search_fields, terms)]
        if isinstance(queryset, QuerySet):
            return queryset.filter(pk__in=[item.pk for item in matching])
        return matching

    def get_schema_operation_parameters(self, view):
        if not getattr(view, 'search_fields', None):
            return []
        parameters = super().get_schema_operation_parameters(view)
        if hasattr(view, 'search_description'):
            parameters[0]['description'] = view.search_description
        return parameters

    @staticmethod
    def _matches(item, search_fields, terms):
        return matches_search_terms((_resolve_attribute_path(item, field) for field in search_fields), terms)


def _resolve_attribute_path(item, path):
    for attribute in path.split('__'):
        item = getattr(item, attribute, None)
        if item is None:
            return ''
    return str(item)
