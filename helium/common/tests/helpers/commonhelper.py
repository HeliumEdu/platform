from unittest import mock

from rest_framework import status


def given_urlopen_response_value(status, mock_urlopen):
    magic_mock = mock.MagicMock()
    magic_mock.getcode.return_value = status
    mock_urlopen.return_value = magic_mock


def verify_all_responses_have_status(test_case, responses, status_code):
    for response in responses:
        test_case.assertEqual(response.status_code, status_code)


def verify_responses_hide_other_users_data(test_case, responses):
    for response in responses:
        if isinstance(response.data, list):
            test_case.assertEqual(response.status_code, status.HTTP_200_OK)
            test_case.assertEqual(len(response.data), 0)
        else:
            test_case.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            test_case.assertIn('matches the given query', response.data['detail'].lower())
