import json
from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.tests.helpers import userhelper
from helium.common.throttles import AnonThrottle, UserThrottle

_PRODUCTION_DEFAULT_THROTTLES = mock.patch.object(APIView, 'throttle_classes', (AnonThrottle, UserThrottle))


@_PRODUCTION_DEFAULT_THROTTLES
class TestCaseSharedIpThrottling(APITestCase):
    def _post_json(self, name, data, **extra):
        return self.client.post(reverse(name), json.dumps(data), content_type='application/json', **extra)

    def _put_json(self, name, data):
        return self.client.put(reverse(name), json.dumps(data), content_type='application/json')

    def test_classmates_behind_one_ip_can_all_log_in(self):
        # GIVEN
        classmates = userhelper.given_users_exist(15)

        # WHEN
        responses = [self._post_json('auth_token_obtain', {'email': user.email, 'password': 'test_pass_1!'})
                     for user in classmates]

        # THEN
        self.assertEqual([r.status_code for r in responses], [status.HTTP_200_OK] * 15)

    def test_repeated_logins_for_one_account_from_one_ip_are_throttled_without_blocking_classmates(self):
        # GIVEN
        target, classmate = userhelper.given_users_exist(2)
        for _ in range(5):
            self._post_json('auth_token_obtain', {'email': target.email, 'password': 'wrong-password'})

        # WHEN
        target_response = self._post_json('auth_token_obtain', {'email': target.email, 'password': 'test_pass_1!'})
        classmate_response = self._post_json('auth_token_obtain',
                                             {'email': classmate.email, 'password': 'test_pass_1!'})

        # THEN
        self.assertEqual(target_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(classmate_response.status_code, status.HTTP_200_OK)

    def test_failed_logins_from_one_address_do_not_lock_the_owner_out_elsewhere(self):
        # GIVEN
        target = userhelper.given_users_exist(1)[0]
        for _ in range(5):
            self._post_json('auth_token_obtain', {'email': target.email, 'password': 'wrong-password'},
                            REMOTE_ADDR='203.0.113.9')

        # WHEN
        response = self._post_json('auth_token_obtain', {'email': target.email, 'password': 'test_pass_1!'},
                                   REMOTE_ADDR='198.51.100.4')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logins_for_one_account_spread_across_addresses_are_throttled(self):
        # GIVEN
        target = userhelper.given_users_exist(1)[0]
        for attempt in range(20):
            self._post_json('auth_token_obtain', {'email': target.email, 'password': 'wrong-password'},
                            REMOTE_ADDR=f'203.0.113.{attempt}')

        # WHEN
        response = self._post_json('auth_token_obtain', {'email': target.email, 'password': 'wrong-password'},
                                   REMOTE_ADDR='198.51.100.4')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_every_spelling_of_an_account_shares_one_login_limit(self):
        # GIVEN
        target = userhelper.given_users_exist(1)[0]
        spellings = [target.email, target.username, target.email.upper(), target.username.upper(), target.email]
        for spelling in spellings:
            self._post_json('auth_token_obtain', {'email': spelling, 'password': 'wrong-password'})

        # WHEN
        response = self._post_json('auth_token_obtain', {'email': target.username, 'password': 'test_pass_1!'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_a_non_string_email_is_rejected_not_an_error(self):
        for name, expected in (('auth_token_obtain', status.HTTP_401_UNAUTHORIZED),
                               ('auth_user_resource_register', status.HTTP_400_BAD_REQUEST)):
            with self.subTest(endpoint=name):
                # WHEN
                response = self._post_json(name, {'email': 123, 'password': 'test_pass_1!'})

                # THEN
                self.assertEqual(response.status_code, expected)

    def test_classmates_behind_one_ip_can_all_register(self):
        # WHEN
        responses = [self._post_json('auth_user_resource_register',
                                     {'email': f'new{i}@school.edu', 'password': 'test_pass_1!',
                                      'time_zone': 'America/Chicago'})
                     for i in range(30)]

        # THEN
        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, [r.status_code for r in responses])

    def test_registering_again_for_one_inbox_is_throttled_including_subaddresses(self):
        # GIVEN
        self._post_json('auth_user_resource_register',
                        {'email': 'same@school.edu', 'password': 'test_pass_1!', 'time_zone': 'America/Chicago'})

        # WHEN
        response = self._post_json('auth_user_resource_register',
                                   {'email': 'Same+again@school.edu', 'password': 'test_pass_1!',
                                    'time_zone': 'America/Chicago'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_registering_with_an_existing_email_does_not_block_its_password_reset(self):
        # GIVEN
        target = userhelper.given_users_exist(1)[0]
        self._post_json('auth_user_resource_register',
                        {'email': target.email, 'password': 'test_pass_1!', 'time_zone': 'America/Chicago'})

        # WHEN
        response = self._put_json('auth_user_resource_forgot', {'email': target.email})

        # THEN
        self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_verification_code_guesses_are_throttled_per_account(self):
        # GIVEN
        userhelper.given_an_inactive_user_exists('target', 'target@school.edu', 'test_pass_1!')
        userhelper.given_an_inactive_user_exists('classmate', 'classmate@school.edu', 'test_pass_1!')
        verify = reverse('auth_user_resource_verify')
        for code in range(5):
            self.client.get(verify, {'email': 'target@school.edu', 'code': code})

        # WHEN
        target_response = self.client.get(verify, {'email': 'target@school.edu', 'code': 6})
        classmate_response = self.client.get(verify, {'email': 'classmate@school.edu', 'code': 6})

        # THEN
        self.assertEqual(target_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertNotEqual(classmate_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_verification_is_throttled_on_the_queried_email_whatever_the_body_says(self):
        # GIVEN
        userhelper.given_an_inactive_user_exists('target', 'target@school.edu', 'test_pass_1!')
        verify = reverse('auth_user_resource_verify')
        for code in range(5):
            self.client.generic('GET', f'{verify}?email=target@school.edu&code={code}',
                                json.dumps({'email': f'decoy{code}@school.edu'}), content_type='application/json')

        # WHEN
        response = self.client.generic('GET', f'{verify}?email=target@school.edu&code=6',
                                       json.dumps({'email': 'decoy-final@school.edu'}),
                                       content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_classmates_behind_one_ip_can_all_refresh_tokens(self):
        # GIVEN
        refresh_tokens = [str(RefreshToken.for_user(user)) for user in userhelper.given_users_exist(15)]

        # WHEN
        responses = [self._post_json('auth_token_refresh', {'refresh': token}) for token in refresh_tokens]

        # THEN
        self.assertEqual([r.status_code for r in responses], [status.HTTP_200_OK] * 15)

    def test_one_users_refreshes_are_throttled_without_blocking_classmates(self):
        # GIVEN
        heavy, classmate = userhelper.given_users_exist(2)
        for _ in range(130):
            self._post_json('auth_token_refresh', {'refresh': str(RefreshToken.for_user(heavy))})

        # WHEN
        heavy_response = self._post_json('auth_token_refresh', {'refresh': str(RefreshToken.for_user(heavy))})
        classmate_response = self._post_json('auth_token_refresh', {'refresh': str(RefreshToken.for_user(classmate))})

        # THEN
        self.assertEqual(heavy_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(classmate_response.status_code, status.HTTP_200_OK)

    def test_invalid_refresh_tokens_are_throttled_per_ip(self):
        # GIVEN
        for _ in range(100):
            self._post_json('auth_token_refresh', {'refresh': 'not-a-token'})

        # WHEN
        response = self._post_json('auth_token_refresh', {'refresh': 'not-a-token'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_classmates_behind_one_ip_can_all_log_out(self):
        # GIVEN
        refresh_tokens = [str(RefreshToken.for_user(user)) for user in userhelper.given_users_exist(15)]

        # WHEN
        responses = [self._post_json('auth_token_blacklist', {'refresh': token}) for token in refresh_tokens]

        # THEN
        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, [r.status_code for r in responses])

    def test_many_users_feeds_polled_from_one_ip_are_not_throttled(self):
        # GIVEN
        slugs = []
        for user in userhelper.given_users_exist(15):
            user.settings.enable_private_slug()
            slugs.append(user.settings.private_slug)

        # WHEN
        responses = [self.client.get(reverse('feed_private_homework_ical', kwargs={'private_slug': slug}))
                     for slug in slugs]

        # THEN
        self.assertEqual([r.status_code for r in responses], [status.HTTP_200_OK] * 15)

    def test_one_feed_polled_too_often_is_throttled_without_limiting_its_owner(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.enable_private_slug()
        feed = reverse('feed_private_homework_ical', kwargs={'private_slug': user.settings.private_slug})
        calendar_provider = APIClient()
        for _ in range(130):
            calendar_provider.get(feed)

        # WHEN
        feed_response = calendar_provider.get(feed)
        owner_response = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(feed_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)

    def test_unknown_feed_slugs_are_throttled_per_ip(self):
        # GIVEN
        for i in range(100):
            self.client.get(reverse('feed_private_homework_ical', kwargs={'private_slug': f'guess{i}'}))

        # WHEN
        response = self.client.get(reverse('feed_private_homework_ical', kwargs={'private_slug': 'guess-final'}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_app_startup_info_from_a_shared_address_is_not_throttled(self):
        # WHEN
        responses = [self.client.get(reverse('resource_info')) for _ in range(100)]

        # THEN
        self.assertEqual([r.status_code for r in responses], [status.HTTP_200_OK] * 100)
