import io
import json
import urllib.error
from unittest import mock

SUBMITTER_EMAIL = 'student@example.com'


def given_a_submission(**overrides):
    submission = {
        'subject': 'Planner shows tasks a day early',
        'email': SUBMITTER_EMAIL,
        'category': 'Bug Report',
        'description': 'Every task shows up one day before its actual date.',
    }
    submission.update(overrides)
    return submission


def given_a_spam_submission(**overrides):
    return given_a_submission(
        subject='Partnership opportunity',
        description="I'm Jane Doe, founder of Acme Leads. We guarantee qualified leads. "
                    'Schedule a call with me: https://calendly.com/example/30min',
        **overrides,
    )


def given_jsm_responds(mock_urlopen, *outcomes):
    mock_urlopen.side_effect = [o if isinstance(o, Exception) else _jsm_response(o) for o in outcomes]


def jsm_error():
    return urllib.error.HTTPError('https://jsm.example', 400, 'Bad Request', hdrs=None, fp=io.BytesIO(b'{}'))


def sent_payload(mock_urlopen, call_index=0):
    return json.loads(mock_urlopen.call_args_list[call_index][0][0].data.decode('utf-8'))


def _jsm_response(body):
    response = mock.MagicMock()
    response.read.return_value = json.dumps(body).encode('utf-8')
    context_manager = mock.MagicMock()
    context_manager.__enter__.return_value = response
    return context_manager
