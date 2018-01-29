from mock import mock

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


def given_urlopen_response_value(status, mock_urlopen):
    magic_mock = mock.MagicMock()
    magic_mock.getcode.return_value = status
    mock_urlopen.return_value = magic_mock
