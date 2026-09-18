import json

from django.test import TestCase
from rest_framework import status


class TestCaseDocs(TestCase):
    def test_docs_publicly_accessible(self):
        # GIVEN

        # WHEN
        response = self.client.get('/docs/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schema_publicly_accessible(self):
        # GIVEN

        # WHEN
        response = self.client.get('/schema/')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schema_documents_resources_not_the_legacy_material_terms(self):
        # GIVEN
        response = self.client.get('/schema/?format=json')
        schema = json.loads(response.content)

        # WHEN
        material_paths = [path for path in schema['paths'] if 'material' in path]
        material_components = [name for name in schema['components']['schemas'] if 'Material' in name]
        material_properties = [
            f'{name}.{prop}'
            for name, component in schema['components']['schemas'].items()
            for prop in component.get('properties', {}) if 'material' in prop
        ]

        material_prose = [text for text in _strings_in(schema) if 'material' in text.lower() and 'support' not in text]

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(material_paths, [])
        self.assertEqual(material_components, [])
        self.assertEqual(material_properties, [])
        self.assertEqual(material_prose, [])
        self.assertIn('/planner/resources/', schema['paths'])
        self.assertIn('/planner/resourcegroups/{resource_group}/resources/{id}/', schema['paths'])


def _strings_in(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _strings_in(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings_in(value)
    elif isinstance(node, str):
        yield node
