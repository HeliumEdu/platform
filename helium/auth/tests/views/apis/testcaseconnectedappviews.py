from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from oauth2_provider.models import get_access_token_model, get_refresh_token_model
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import oauthhelper, userhelper


def given_a_connected_app(user, name, token, scope='planner:read planner:import', expires_in=timedelta(hours=1)):
    application = oauthhelper.given_oauth_application_exists(name=name)
    access_token = oauthhelper.given_oauth_token_exists(user, application, scope=scope, token=token,
                                                        resource=list(settings.OAUTH_CONNECTOR_RESOURCES),
                                                        expires_in=expires_in)
    get_refresh_token_model().objects.create(user=user, application=application, token=f'{token}-refresh',
                                             access_token=access_token)
    return application


class TestCaseConnectedAppViews(APITestCase):
    def test_login_required(self):
        # WHEN
        responses = [
            self.client.get(reverse('auth_user_connectedapps_list')),
            self.client.delete(reverse('auth_user_connectedapps_detail', kwargs={'pk': 9999})),
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_connected_apps(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        other_user = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        given_a_connected_app(user, 'Claude', 'claude-token')
        given_a_connected_app(user, 'Study App', 'study-token', scope='planner:read')
        given_a_connected_app(other_user, 'Not Mine', 'other-token')
        revoked = given_a_connected_app(user, 'Revoked', 'revoked-token', expires_in=timedelta(hours=-1))
        get_refresh_token_model().objects.filter(application=revoked).update(revoked=revoked.created)

        # WHEN
        response = self.client.get(reverse('auth_user_connectedapps_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(['Study App', 'Claude'], [app['name'] for app in response.data])
        self.assertEqual([{'scope': 'planner:read',
                           'description': 'Read your assignments, events, notes, classes, resources, and grades'}],
                         response.data[0]['scopes'])
        self.assertIsNotNone(response.data[0]['last_used_at'])

    def test_list_pages_on_request(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        given_a_connected_app(user, 'Claude', 'claude-token')
        given_a_connected_app(user, 'Study App', 'study-token')

        # WHEN
        response = self.client.get(reverse('auth_user_connectedapps_list') + '?page_size=1')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, response.data['count'])
        self.assertEqual(['Study App'], [app['name'] for app in response.data['results']])

    def test_revoke_a_connected_app(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        claude = given_a_connected_app(user, 'Claude', 'claude-token')
        study_app = given_a_connected_app(user, 'Study App', 'study-token')

        # WHEN
        response = self.client.delete(reverse('auth_user_connectedapps_detail', kwargs={'pk': claude.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(get_access_token_model().objects.filter(application=claude).exists())
        self.assertFalse(get_refresh_token_model().objects.filter(application=claude).exists())
        self.assertTrue(get_access_token_model().objects.filter(application=study_app).exists())
        self.assertEqual(['Study App'],
                         [app['name'] for app in self.client.get(reverse('auth_user_connectedapps_list')).data])

    def test_revoking_an_app_not_connected_is_not_found(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        other_user = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        not_mine = given_a_connected_app(other_user, 'Not Mine', 'other-token')

        # WHEN
        responses = [
            self.client.delete(reverse('auth_user_connectedapps_detail', kwargs={'pk': not_mine.pk})),
            self.client.delete(reverse('auth_user_connectedapps_detail', kwargs={'pk': 9999})),
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(get_access_token_model().objects.filter(application=not_mine).exists())

    def test_an_oauth_token_cannot_manage_connected_apps(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        claude = given_a_connected_app(user, 'Claude', 'claude-token')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer claude-token')

        # WHEN
        responses = [
            self.client.get(reverse('auth_user_connectedapps_list')),
            self.client.delete(reverse('auth_user_connectedapps_detail', kwargs={'pk': claude.pk})),
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(get_access_token_model().objects.filter(application=claude).exists())
