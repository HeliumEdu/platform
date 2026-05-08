__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json

from django.test import TestCase


class TestCaseHandlerViews(TestCase):
    def test_unknown_route_returns_json_404(self):
        # GIVEN/WHEN
        response = self.client.get('/this-route-does-not-exist/')

        # THEN
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {'detail': 'Route not found.'})
