from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'


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
    token = Token.objects.create(user=user)

    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    return user
