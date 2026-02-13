__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os
from unittest import mock

from rest_framework import status


def given_urlopen_mock_from_file(filename, mock_urlopen, status_code=status.HTTP_200_OK,
                                  etag=None, last_modified=None):
    data = open(os.path.join(os.path.dirname(__file__), '..', filename), 'r').read()

    magic_mock = mock.MagicMock()
    magic_mock.getcode.return_value = status_code
    magic_mock.read.return_value = data

    def getheader(name):
        if name == 'ETag':
            return etag
        if name == 'Last-Modified':
            return last_modified
        return None

    magic_mock.getheader.side_effect = getheader
    mock_urlopen.return_value = magic_mock


def given_urlopen_mock_304_not_modified(mock_urlopen):
    """Mock a 304 Not Modified response."""
    magic_mock = mock.MagicMock()
    magic_mock.getcode.return_value = status.HTTP_304_NOT_MODIFIED
    mock_urlopen.return_value = magic_mock
