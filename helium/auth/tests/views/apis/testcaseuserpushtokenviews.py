import json
from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.models.userpushtoken import UserPushToken
from helium.auth.tests.helpers import userhelper


def given_push_tokens_registered_in_order(user, count):
    now = timezone.now()
    push_tokens = []
    for i in range(count):
        push_token = userhelper.given_user_push_token_exists(user, token=f'token{i}', device_id=f'device{i}')
        UserPushToken.objects.filter(pk=push_token.pk).update(updated_at=now - timedelta(days=count - i))
        push_tokens.append(push_token)

    return push_tokens


class TestCasePushTokenViews(APITestCase):
    def test_push_token_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('auth_user_pushtoken_list')),
            self.client.post(reverse('auth_user_pushtoken_list')),
            self.client.get(reverse('auth_user_pushtoken_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('auth_user_pushtoken_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_push_tokens(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        userhelper.given_user_push_token_exists(user1)
        userhelper.given_user_push_token_exists(user2, token='token2', device_id='device2')
        userhelper.given_user_push_token_exists(user2, token='token3', device_id='device3')

        # WHEN
        response1 = self.client.get(reverse('auth_user_pushtoken_list'))
        response2 = self.client.get(reverse('auth_user_pushtoken_list') + f'?device_id=device2')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(UserPushToken.objects.count(), 3)
        self.assertEqual(len(response1.data), 2)
        self.assertEqual(len(response2.data), 1)

    def test_create_push_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'device_id': 'device1',
            'token': 'token1',
            'user': user.pk
        }
        response = self.client.post(reverse('auth_user_pushtoken_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserPushToken.objects.count(), 1)
        push_token = UserPushToken.objects.get(pk=response.data['id'])
        userhelper.verify_push_token_matches(self, push_token, response.data)

    def test_delete_push_token_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        push_token = userhelper.given_user_push_token_exists(user)

        # WHEN
        response = self.client.delete(reverse('auth_user_pushtoken_detail',
                                              kwargs={'pk': push_token.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserPushToken.objects.filter(pk=push_token.pk).exists())
        self.assertEqual(UserPushToken.objects.count(), 0)

    @override_settings(MAX_PUSH_TOKENS_PER_USER=3)
    def test_create_push_token_beyond_the_limit_evicts_the_least_recently_registered(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        oldest, middle, newest = given_push_tokens_registered_in_order(user, 3)

        # WHEN
        response = self.client.post(reverse('auth_user_pushtoken_list'),
                                    json.dumps({'device_id': 'new_device', 'token': 'new_token'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(UserPushToken.objects.filter(user=user).values_list('pk', flat=True),
                              [middle.pk, newest.pk, response.data['id']])

    @override_settings(MAX_PUSH_TOKENS_PER_USER=3)
    def test_create_push_token_up_to_the_limit_evicts_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        given_push_tokens_registered_in_order(user, 2)

        # WHEN
        response = self.client.post(reverse('auth_user_pushtoken_list'),
                                    json.dumps({'device_id': 'new_device', 'token': 'new_token'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserPushToken.objects.filter(user=user).count(), 3)

    @override_settings(MAX_PUSH_TOKENS_PER_USER=3)
    def test_reregistering_the_oldest_device_at_the_limit_keeps_it(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        oldest, middle, newest = given_push_tokens_registered_in_order(user, 3)

        # WHEN
        response = self.client.post(reverse('auth_user_pushtoken_list'),
                                    json.dumps({'device_id': oldest.device_id, 'token': 'refreshed_token'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(UserPushToken.objects.filter(user=user).values_list('pk', flat=True),
                              [oldest.pk, middle.pk, newest.pk])

    @override_settings(MAX_PUSH_TOKENS_PER_USER=3)
    def test_eviction_leaves_other_users_tokens_alone(self):
        # GIVEN
        other_user = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        other_push_tokens = given_push_tokens_registered_in_order(other_user, 3)
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        given_push_tokens_registered_in_order(user, 3)

        # WHEN
        self.client.post(reverse('auth_user_pushtoken_list'),
                         json.dumps({'device_id': 'new_device', 'token': 'new_token'}),
                         content_type='application/json')

        # THEN
        self.assertEqual(UserPushToken.objects.filter(user=user).count(), 3)
        self.assertCountEqual(UserPushToken.objects.filter(user=other_user).values_list('pk', flat=True),
                              [push_token.pk for push_token in other_push_tokens])
