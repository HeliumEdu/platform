import json

from django.test import TestCase, override_settings
from drf_spectacular.generators import SchemaGenerator
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


class TestCaseDocsSidebar(TestCase):
    def test_every_tag_is_in_a_sidebar_group(self):
        # GIVEN
        response = self.client.get('/schema/?format=json')
        schema = json.loads(response.content)
        grouped = {tag for group in schema['x-tagGroups'] for tag in group['tags']}

        # WHEN
        hidden = sorted({f'{tag}: {method.upper()} {path}'
                         for path, operations in schema['paths'].items()
                         for method, operation in operations.items()
                         for tag in operation.get('tags') or ['(untagged)'] if tag not in grouped})

        # THEN
        self.assertEqual(hidden, [], 'Redoc hides operations whose tag is in no `TAG_GROUPS` group')


class TestCaseDocsResponses(TestCase):
    def setUp(self):
        # As `make build-docs` generates it: offline, so drf-spectacular's stand-in request host isn't allowed
        with override_settings(ALLOWED_HOSTS=['api.heliumedu.com']):
            self.schema = SchemaGenerator().get_schema(request=None, public=True)

    def test_every_read_documents_its_response(self):
        # WHEN
        undocumented = [path for path, operations in self.schema['paths'].items()
                        if '200' in operations.get('get', {}).get('responses', {})
                        and not operations['get']['responses']['200'].get('content')]

        # THEN
        self.assertEqual(undocumented, [], 'a view skipped during schema generation loses its response schema')

    def test_only_reads_are_paged(self):
        # WHEN
        paged_writes = [f'{method.upper()} {path}'
                        for path, operations in self.schema['paths'].items()
                        for method, operation in operations.items() if method in ('post', 'put', 'patch', 'delete')
                        for response in operation.get('responses', {}).values()
                        if 'Paginated' in json.dumps(response.get('content', {}))]

        # THEN
        self.assertEqual(paged_writes, [])
        self.assertEqual('array', self.schema['paths']['/planner/attachments/']['post']['responses']['201']['content']
                         ['application/json']['schema']['type'])


def _strings_in(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _strings_in(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings_in(value)
    elif isinstance(node, str):
        yield node
