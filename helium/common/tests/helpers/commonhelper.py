import array
import os
import struct
from unittest import mock

from django.utils import translation
from rest_framework import status

NOT_FOUND_MESSAGE_PATTERN = r'^(Item|Class|Group|Resource) not found\.$'


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
            test_case.assertRegex(response.data['detail'], NOT_FOUND_MESSAGE_PATTERN)


def given_sent_emails_are_recorded(*mock_sends):
    sent = []

    def record(template_name, context, subject, to, **kwargs):
        sent.append((template_name, subject, translation.get_language()))

    for mock_send in mock_sends:
        mock_send.side_effect = record

    return sent


def given_a_translation_catalog(locale_path, language, translations):
    """
    Compile ``translations`` (msgid to msgstr) into a Django catalog for ``language`` under ``locale_path``, laid
    out as ``LOCALE_PATHS`` expects.
    """
    messages = {b'': b'Content-Type: text/plain; charset=UTF-8\n'}
    messages.update({msgid.encode(): msgstr.encode() for msgid, msgstr in translations.items()})

    keys = sorted(messages)
    ids = strs = b''
    entries = []
    for key in keys:
        entries.append((len(ids), len(key), len(strs), len(messages[key])))
        ids += key + b'\0'
        strs += messages[key] + b'\0'

    key_start = 7 * 4 + 16 * len(keys)
    value_start = key_start + len(ids)
    key_offsets = [value for id_offset, id_length, _, _ in entries for value in (id_length, id_offset + key_start)]
    value_offsets = [value for _, _, str_offset, str_length in entries
                     for value in (str_length, str_offset + value_start)]

    directory = os.path.join(locale_path, language, 'LC_MESSAGES')
    os.makedirs(directory)
    with open(os.path.join(directory, 'django.mo'), 'wb') as catalog:
        catalog.write(struct.pack('Iiiiiii', 0x950412de, 0, len(keys), 7 * 4, 7 * 4 + len(keys) * 8, 0, 0))
        catalog.write(array.array('i', key_offsets + value_offsets).tobytes())
        catalog.write(ids)
        catalog.write(strs)
