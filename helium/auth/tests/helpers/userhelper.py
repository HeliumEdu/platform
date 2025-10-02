__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import json

from django.contrib.auth import get_user_model
from django.urls import reverse

from helium.auth.models.userpushtoken import UserPushToken


def given_an_inactive_user_exists(username='test_user', email='user@test.com', password='test_pass_1!'):
    user = get_user_model().objects.create_user(username=username,
                                                email=email,
                                                password=password)

    return user


def given_a_user_exists(username='test_user', email='user@test.com', password='test_pass_1!'):
    user = given_an_inactive_user_exists(username, email, password)

    user.is_active = True

    user.save()

    return user


def given_a_user_exists_and_is_authenticated(client, username='test_user', email='user@test.com',
                                             password='test_pass_1!'):
    user = given_a_user_exists(username, email, password)

    data = {
        'username': username,
        'password': 'test_pass_1!'
    }
    response = client.post(reverse('auth_token_obtain'),
                           json.dumps(data),
                           content_type='application/json')

    client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])

    user.access = response.data['access']
    user.refresh = response.data['refresh']

    return user


def given_user_push_token_exists(user, token='token1', device_id='device1'):
    push_token = UserPushToken.objects.create(user=user, token=token, device_id=device_id)

    return push_token


def verify_push_token_matches(test_case, push_token, data):
    test_case.assertEqual(push_token.device_id, data['device_id'])
    test_case.assertEqual(push_token.token, data['token'])
    test_case.assertEqual(push_token.user.pk, data['user'])
