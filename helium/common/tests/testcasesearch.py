from types import SimpleNamespace

from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from helium.common.search import HeliumSearchFilter


def _view(**attrs):
    return SimpleNamespace(**attrs)


def _request(search):
    return Request(APIRequestFactory().get('/', {'search': search} if search is not None else {}))


class TestCaseHeliumSearchFilter(TestCase):
    def test_filters_in_memory_items_by_attribute_paths(self):
        # GIVEN
        items = [
            SimpleNamespace(title='Lab', course=SimpleNamespace(title='Biología')),
            SimpleNamespace(title='Essay', course=SimpleNamespace(title='History')),
            SimpleNamespace(title='Reading', course=None),
        ]

        # WHEN
        matching = HeliumSearchFilter().filter_queryset(_request('biologia lab'), items, _view(search_fields=('title', 'course__title')))

        # THEN
        self.assertEqual([item.title for item in matching], ['Lab'])

    def test_no_search_fields_or_no_terms_returns_items_untouched(self):
        # GIVEN
        items = [SimpleNamespace(title='x')]

        # WHEN
        without_fields = HeliumSearchFilter().filter_queryset(_request('x'), items, _view())
        without_terms = HeliumSearchFilter().filter_queryset(_request('  .. '), items, _view(search_fields=('title',)))

        # THEN
        self.assertIs(without_fields, items)
        self.assertIs(without_terms, items)

    def test_schema_documents_search_only_for_views_that_declare_search_fields(self):
        # GIVEN
        undeclared = _view()
        declared = _view(search_fields=('title',), search_description='Search by title.')

        # WHEN
        undeclared_params = HeliumSearchFilter().get_schema_operation_parameters(undeclared)
        declared_params = HeliumSearchFilter().get_schema_operation_parameters(declared)

        # THEN
        self.assertEqual(undeclared_params, [])
        self.assertEqual([(p['name'], p['description']) for p in declared_params], [('search', 'Search by title.')])
