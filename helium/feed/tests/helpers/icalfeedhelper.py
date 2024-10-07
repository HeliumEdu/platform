__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.2"

import os
from unittest import mock

from rest_framework import status


def given_urlopen_mock_from_file(filename, mock_urlopen, status_code=status.HTTP_200_OK):
    data = open(os.path.join(os.path.dirname(__file__), '..', filename), 'r').read()

    magic_mock = mock.MagicMock()
    magic_mock.getcode.return_value = status_code
    magic_mock.read.return_value = data
    mock_urlopen.return_value = magic_mock
