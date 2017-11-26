"""
Helper for User models in testing.
"""

from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


def given_a_user_exists(username='test_user', email='test@heliumedu.com'):
    user = get_user_model().objects.create_user(username=username,
                                                email=email,
                                                password='test_pass_1!')
    user.address_1 = 'address 1'
    user.city = 'city'
    user.state = 'CA'
    user.postal_code = '94530'
    user.phone = '555-5555'

    user.save()

    return user


def given_a_user_exists_and_is_logged_in(test_case):
    user = given_a_user_exists()

    test_case.client.login(username=user.get_username(), password='test_pass_1!')

    return user
