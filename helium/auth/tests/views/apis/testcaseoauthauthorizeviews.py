from unittest import mock

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.cimd import SafeMetadataFetcher
from oauth2_provider.models import (
    get_access_token_model,
    get_application_model,
    get_refresh_token_model,
)
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.models import UserClientActivity
from helium.auth.tests.helpers import oauthhelper, userhelper

CONNECTOR_RESOURCE = settings.OAUTH_CONNECTOR_RESOURCES[0]


class TestCaseOAuthAuthorizeViews(APITestCase):
    def setUp(self):
        self.application = oauthhelper.given_oauth_application_exists()

    def authorize_url(self, **overrides):
        query = oauthhelper.authorization_query(self.application.client_id, **overrides)
        return f"{reverse('auth_oauth_authorize')}?{query}"

    def exchange_code(self, code, **overrides):
        self.client.credentials()
        data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': oauthhelper.REDIRECT_URI,
                'client_id': self.application.client_id, 'code_verifier': oauthhelper.CODE_VERIFIER}
        data.update(overrides)
        return self.client.post(reverse('oauth2_provider:token'), data)

    def given_an_authorization_code(self, **overrides):
        response = self.client.post(self.authorize_url(**overrides), {'allow': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return oauthhelper.redirect_params(response.data['redirect_uri'])['code']

    def test_describe_authorization(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(self.authorize_url())

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['client_name'], 'MCP Client')
        self.assertEqual(response.data['redirect_uri'], oauthhelper.REDIRECT_URI)
        self.assertEqual({scope['scope'] for scope in response.data['scopes']}, {'planner:read', 'planner:import'})
        self.assertTrue(all(scope['description'] for scope in response.data['scopes']))

    def test_request_without_scopes_asks_only_to_read(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(self.authorize_url(scope=None))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([scope['scope'] for scope in response.data['scopes']], ['planner:read'])

    def test_approval_issues_a_code_that_exchanges_for_tokens(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(self.authorize_url(), {'allow': True}, format='json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['redirect_uri'].startswith(oauthhelper.REDIRECT_URI))
        params = oauthhelper.redirect_params(response.data['redirect_uri'])
        self.assertEqual(params['state'], 'xyz')
        self.assertEqual(params['iss'], settings.PROJECT_API_HOST)

        # WHEN
        token_response = self.exchange_code(params['code'])

        # THEN
        self.assertEqual(token_response.status_code, status.HTTP_200_OK, token_response.content)
        tokens = token_response.json()
        self.assertEqual(tokens['scope'], 'planner:read planner:import')
        self.assertEqual(tokens['expires_in'], 3600)
        self.assertIn('refresh_token', tokens)
        self.assertEqual(get_access_token_model().objects.get(user=user).application, self.application)

    def test_issued_token_reads_the_planner(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        tokens = self.exchange_code(self.given_an_authorization_code()).json()

        # WHEN
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        user_response = self.client.get(reverse('auth_user_detail'))
        homework_response = self.client.get(reverse('planner_homework_list'))

        # THEN
        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
        self.assertEqual(homework_response.status_code, status.HTTP_200_OK)

    def test_token_for_the_connector_resource_is_accepted_by_the_api(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        code = self.given_an_authorization_code(resource=CONNECTOR_RESOURCE)
        tokens = self.exchange_code(code, resource=CONNECTOR_RESOURCE).json()

        # WHEN
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        response = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_access_token_model().objects.get().resource, [CONNECTOR_RESOURCE])

    def test_token_exchange_counts_as_activity(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.last_activity = timezone.now() - timezone.timedelta(days=400)
        user.deletion_warning_count = 1
        user.save()
        code = self.given_an_authorization_code()

        # WHEN
        self.exchange_code(code)

        # THEN
        user.refresh_from_db()
        self.assertGreater(user.last_activity, timezone.now() - timezone.timedelta(minutes=1))
        self.assertEqual(user.deletion_warning_count, 0)
        self.assertTrue(UserClientActivity.objects.filter(user=user,
                                                          client=UserClientActivity.CLIENT_CONNECTOR).exists())

    def test_refresh_rotates_the_refresh_token(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        tokens = self.exchange_code(self.given_an_authorization_code()).json()

        # WHEN
        response = self.client.post(reverse('oauth2_provider:token'), {
            'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token'],
            'client_id': self.application.client_id})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertNotEqual(response.json()['refresh_token'], tokens['refresh_token'])

    def test_denial_redirects_with_access_denied(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(self.authorize_url(), {'allow': False}, format='json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        params = oauthhelper.redirect_params(response.data['redirect_uri'])
        self.assertEqual(params['error'], 'access_denied')
        self.assertEqual(params['state'], 'xyz')
        self.assertEqual(params['iss'], settings.PROJECT_API_HOST)
        self.assertNotIn('code', params)

    def test_unknown_client_is_never_redirected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        query = oauthhelper.authorization_query('not-a-client')
        responses = [self.client.get(f"{reverse('auth_oauth_authorize')}?{query}"),
                     self.client.post(f"{reverse('auth_oauth_authorize')}?{query}", {'allow': False}, format='json')]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertNotIn('redirect_uri', response.data)

    def test_unregistered_redirect_uri_is_never_redirected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(self.authorize_url(redirect_uri='https://attacker.example/callback'),
                                    {'allow': True}, format='json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('redirect_uri', response.data)

    def test_pkce_is_required(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(self.authorize_url(code_challenge=None, code_challenge_method=None))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(oauthhelper.redirect_params(response.data['redirect_uri'])['error'], 'invalid_request')

    def test_plain_pkce_is_refused(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        url = self.authorize_url(code_challenge=oauthhelper.CODE_VERIFIER, code_challenge_method='plain')

        # WHEN
        responses = [self.client.get(url), self.client.post(url, {'allow': True}, format='json')]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(oauthhelper.redirect_params(response.data['redirect_uri'])['error'], 'invalid_request')

    def test_resource_outside_helium_is_refused(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(self.authorize_url(resource='https://other.example/mcp'), {'allow': True},
                                    format='json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(oauthhelper.redirect_params(response.data['redirect_uri'])['error'], 'invalid_target')

    def test_unknown_scope_is_refused(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(self.authorize_url(scope='planner:read account:delete'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        params = oauthhelper.redirect_params(response.data['redirect_uri'])
        self.assertEqual(params['error'], 'invalid_scope')
        self.assertEqual(params['iss'], settings.PROJECT_API_HOST)

    def test_only_an_app_session_can_consent(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        oauthhelper.given_oauth_token_exists(user, self.application)

        # WHEN
        self.client.credentials(HTTP_AUTHORIZATION='Bearer opaque-oauth-token')
        with_oauth_token = self.client.post(self.authorize_url(), {'allow': True}, format='json')
        self.client.credentials()
        without_session = self.client.post(self.authorize_url(), {'allow': True}, format='json')

        # THEN
        self.assertEqual(with_oauth_token.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(without_session.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(OAUTH2_PROVIDER={**settings.OAUTH2_PROVIDER, 'CIMD_ALLOWED_HOSTS': ['mcp-client.example']})
class TestCaseOAuthClientMetadataDocuments(APITestCase):
    CLIENT_ID = 'https://mcp-client.example/oauth/client-metadata'

    def given_metadata(self, client_id):
        return {'client_id': client_id, 'client_name': 'MCP Client', 'redirect_uris': [oauthhelper.REDIRECT_URI],
                'grant_types': ['authorization_code', 'refresh_token'], 'token_endpoint_auth_method': 'none'}, 3600

    def test_allowed_client_registers_from_its_metadata_document(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        query = oauthhelper.authorization_query(self.CLIENT_ID)

        # WHEN
        with mock.patch.object(SafeMetadataFetcher, 'fetch', return_value=self.given_metadata(self.CLIENT_ID)):
            response = self.client.get(f"{reverse('auth_oauth_authorize')}?{query}")

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['client_name'], 'MCP Client')
        self.assertTrue(get_application_model().objects.filter(client_id=self.CLIENT_ID).exists())

    def test_client_metadata_from_another_host_is_refused(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        client_id = 'https://evil.example/oauth/client.json'
        query = oauthhelper.authorization_query(client_id)

        # WHEN
        with mock.patch.object(SafeMetadataFetcher, 'fetch', return_value=self.given_metadata(client_id)) as fetch:
            response = self.client.get(f"{reverse('auth_oauth_authorize')}?{query}")

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('redirect_uri', response.data)
        fetch.assert_not_called()
        self.assertFalse(get_application_model().objects.filter(client_id=client_id).exists())


class TestCaseOAuthServerMetadata(APITestCase):
    def test_metadata(self):
        # WHEN
        response = self.client.get(reverse('oauth_server_metadata'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metadata = response.json()
        self.assertEqual(metadata['issuer'], settings.PROJECT_API_HOST)
        self.assertEqual(metadata['authorization_endpoint'], f'{settings.PROJECT_APP_HOST}/connect')
        self.assertTrue(metadata['token_endpoint'].endswith('/auth/oauth/token/'))
        self.assertTrue(metadata['revocation_endpoint'].endswith('/auth/oauth/revoke/'))
        self.assertEqual(metadata['code_challenge_methods_supported'], ['S256'])
        self.assertEqual(metadata['response_types_supported'], ['code'])
        self.assertEqual(metadata['grant_types_supported'], ['authorization_code', 'refresh_token'])
        self.assertEqual(metadata['token_endpoint_auth_methods_supported'], ['none'])
        self.assertTrue(metadata['client_id_metadata_document_supported'])
        self.assertTrue(metadata['authorization_response_iss_parameter_supported'])
        self.assertEqual(sorted(metadata['scopes_supported']), ['planner:import', 'planner:read'])
        self.assertNotIn('registration_endpoint', metadata)
        self.assertNotIn('introspection_endpoint', metadata)


class TestCaseOAuthTokenAccess(APITestCase):
    def setUp(self):
        self.application = oauthhelper.given_oauth_application_exists()
        self.user = userhelper.given_a_user_exists()

    def given_token(self, scope='planner:read planner:import'):
        oauthhelper.given_oauth_token_exists(self.user, self.application, scope=scope)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer opaque-oauth-token')

    def test_read_scope_reaches_only_planner_reads(self):
        # GIVEN
        self.given_token(scope='planner:read')

        # WHEN / THEN
        for url_name in ('auth_user_detail', 'planner_coursegroups_list', 'planner_courses_list',
                         'planner_courseschedules_list', 'planner_categories_list', 'planner_resource_grades',
                         'planner_notes_list', 'planner_resourcegroups_list', 'planner_resources_list'):
            self.assertEqual(self.client.get(reverse(url_name)).status_code, status.HTTP_200_OK, url_name)
        self.assertEqual(self.client.get(reverse('planner_homework_list')).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse('planner_events_list')).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(reverse('importexport_import'), {}, format='multipart').status_code,
                         status.HTTP_403_FORBIDDEN)

    def test_import_scope_reaches_only_import(self):
        # GIVEN
        self.given_token(scope='planner:import')

        # WHEN / THEN
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse('planner_coursegroups_list')).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(reverse('importexport_import'), {}, format='multipart').status_code,
                         status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(reverse('planner_homework_list')).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse('planner_notes_list')).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse('planner_resources_list')).status_code, status.HTTP_403_FORBIDDEN)

    def test_account_and_destructive_endpoints_are_refused(self):
        # GIVEN
        self.given_token()

        # WHEN
        responses = {
            'change password': self.client.put(reverse('auth_user_detail'), {'password': 'x'}, format='json'),
            'delete account': self.client.delete(reverse('auth_user_resource_delete')),
            'settings': self.client.put(reverse('auth_user_settings_detail'), {}, format='json'),
            'api token': self.client.post(reverse('auth_api_token')),
            'export': self.client.get(reverse('importexport_export')),
            'delete all events': self.client.delete(reverse('planner_events_resource_delete')),
            'create course group': self.client.post(reverse('planner_coursegroups_list'), {}, format='json'),
            'create resource group': self.client.post(reverse('planner_resourcegroups_list'), {}, format='json'),
            'consent': self.client.post(reverse('auth_oauth_authorize'), {'allow': True}, format='json'),
        }

        # THEN
        for name, response in responses.items():
            self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), name)
        self.assertTrue(self.user.check_password('test_pass_1!'))

    def test_expired_token_is_refused(self):
        # GIVEN
        oauthhelper.given_oauth_token_exists(self.user, self.application,
                                             expires_in=-timezone.timedelta(minutes=1))
        self.client.credentials(HTTP_AUTHORIZATION='Bearer opaque-oauth-token')

        # WHEN
        response = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pending_delete_and_inactive_accounts_are_refused(self):
        # GIVEN
        self.given_token()

        for field, value in (('deletion_requested_at', timezone.now()), ('is_active', False)):
            with self.subTest(field=field):
                original = getattr(self.user, field)
                setattr(self.user, field, value)
                self.user.save()

                # WHEN
                response = self.client.get(reverse('auth_user_detail'))

                # THEN
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                setattr(self.user, field, original)
                self.user.save()

    def test_password_change_revokes_grants(self):
        # GIVEN
        self.given_token()
        get_refresh_token_model().objects.create(user=self.user, application=self.application, token='refresh-1',
                                                 access_token=get_access_token_model().objects.get())
        userhelper.reauthenticate(self.client, self.user)

        # WHEN
        self.client.put(reverse('auth_user_detail'), {'old_password': 'test_pass_1!', 'password': 'new_pass_1!'},
                        format='json')

        # THEN
        self.assertFalse(get_access_token_model().objects.filter(user=self.user).exists())
        self.assertFalse(get_refresh_token_model().objects.filter(user=self.user).exists())
        self.client.credentials(HTTP_AUTHORIZATION='Bearer opaque-oauth-token')
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_jwt_keeps_its_error_code(self):
        # GIVEN
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not.a.jwt')

        # WHEN
        response = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['code'], 'token_not_valid')

    def test_unknown_opaque_token_is_refused(self):
        # GIVEN
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-real-token')

        # WHEN
        response = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
