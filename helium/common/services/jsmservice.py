import base64
import json
import logging
import mimetypes
import urllib.error
import urllib.request
import uuid
from typing import List, Optional

from django.conf import settings

from helium.common.utils import metricutils
from helium.common.utils.commonutils import HeliumError, redact_email
from helium.common.utils.httputils import urlopen_secure

logger = logging.getLogger(__name__)

_JSM_REQUEST_TIMEOUT_SECONDS = 15


class JsmRequestException(HeliumError):
    """Raised when a JSM service desk request cannot be created or an attachment cannot be uploaded."""

    def __init__(self, message='Failed to create JSM service desk request', original_error=None):
        self.original_error = original_error
        super().__init__(message)


class JsmAttachmentException(JsmRequestException):
    """Raised when a JSM service desk request was created, but its attachments could not be uploaded."""

    def __init__(self, issue_key, original_error=None):
        self.issue_key = issue_key
        super().__init__(f'Failed to upload attachments to {issue_key}', original_error)


def _auth_header():
    raw = f'{settings.JSM_SERVICE_ACCOUNT_EMAIL}:{settings.JSM_API_TOKEN}'
    encoded = base64.b64encode(raw.encode('utf-8')).decode('ascii')
    return f'Basic {encoded}'


def _request_type_id_for(category):
    return settings.JSM_REQUEST_TYPE_ID_MAP.get(category, settings.JSM_REQUEST_TYPE_ID)


def _spam_reporter_email():
    local_part, _, domain = settings.ADMIN_EMAIL_ADDRESS.rpartition('@')
    return f'{local_part}+spam@{domain}'


def _open(request):
    try:
        with urlopen_secure(request, timeout=_JSM_REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = e.read().decode('utf-8')
        except Exception:
            pass
        logger.warning(f'JSM API returned HTTP {e.code} for {request.get_full_url()}: {detail}')
        raise JsmRequestException(f'JSM API returned HTTP {e.code}', original_error=e) from e
    except (urllib.error.URLError, TimeoutError) as e:
        logger.warning(f'JSM API transport failure for {request.get_full_url()}: {e}')
        raise JsmRequestException('JSM API transport failure', original_error=e) from e
    except Exception as e:
        logger.error('Unexpected error calling JSM API', exc_info=True)
        raise JsmRequestException('Unexpected error calling JSM API', original_error=e) from e


def _post_json(path, payload):
    url = f'{settings.JSM_API_BASE}{path}'
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': _auth_header(),
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        method='POST',
    )
    return _open(request)


def _attach_temporary_file(uploaded_file):
    # TODO(verify-against-live-HS): confirm the multipart field name ("file"), that the
    #  X-Atlassian-Token: no-check header is required, and the exact shape of the
    #  temporaryAttachments response (id key) against the live HS instance.
    boundary = uuid.uuid4().hex
    filename = uploaded_file.name or 'attachment'
    content_type = getattr(uploaded_file, 'content_type', None) \
        or mimetypes.guess_type(filename)[0] \
        or 'application/octet-stream'

    parts = [
        f'--{boundary}'.encode('utf-8'),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode('utf-8'),
        f'Content-Type: {content_type}'.encode('utf-8'),
        b'',
        uploaded_file.read(),
        f'--{boundary}--'.encode('utf-8'),
        b'',
    ]
    data = b'\r\n'.join(parts)

    url = f'{settings.JSM_API_BASE}/rest/servicedeskapi/servicedesk/{settings.JSM_SERVICE_DESK_ID}/attachTemporaryFile'
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': _auth_header(),
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Accept': 'application/json',
            'X-Atlassian-Token': 'no-check',
        },
        method='POST',
    )

    response = _open(request)
    temporary_attachments = (response or {}).get('temporaryAttachments', [])
    return [ta['temporaryAttachmentId'] for ta in temporary_attachments]


def _attach_to_request(issue_key, temporary_attachment_ids):
    # TODO(verify-against-live-HS): confirm the attachment payload field names
    #  (temporaryAttachmentIds, public) against the live HS instance.
    payload = {
        'temporaryAttachmentIds': temporary_attachment_ids,
        'public': True,
    }
    _post_json(f'/rest/servicedeskapi/request/{issue_key}/attachment', payload)


def _attach_all(issue_key, attachments):
    if not attachments:
        return
    if not issue_key:
        logger.warning('JSM request created without an issueKey; skipping attachments')
        return

    try:
        temporary_attachment_ids = []
        for f in attachments:
            temporary_attachment_ids.extend(_attach_temporary_file(f))
        if temporary_attachment_ids:
            _attach_to_request(issue_key, temporary_attachment_ids)
    except Exception as e:
        raise JsmAttachmentException(issue_key, original_error=e) from e


def _build_payload(subject, category, description, reporter_email):
    request_field_values = {
        'summary': f'{category}: {subject}',
        'description': description,
    }

    # TODO(verify-against-live-HS): GET servicedeskapi/requesttype/{id}/field for each mapped
    #  request type to confirm no additional required fields exist beyond summary/description
    #  (and that the target request type has no form-only required ProForma field). If a
    #  category custom field exists, set JSM_CATEGORY_FIELD_ID and include it here.
    if settings.JSM_CATEGORY_FIELD_ID:
        request_field_values[settings.JSM_CATEGORY_FIELD_ID] = category

    return {
        'serviceDeskId': str(settings.JSM_SERVICE_DESK_ID),
        'requestTypeId': str(_request_type_id_for(category)),
        'raiseOnBehalfOf': reporter_email,
        'requestFieldValues': request_field_values,
    }


def _create_request(payload, attachments, metric_prefix, log_suffix):
    try:
        response = _post_json('/rest/servicedeskapi/request', payload)
        issue_key = (response or {}).get('issueKey')

        _attach_all(issue_key, list(attachments or []))

        metricutils.increment(f'{metric_prefix}.sent')
        logger.info(f'Support contact created in JSM ({issue_key or "unknown"}) {log_suffix}')

        return issue_key
    except JsmRequestException:
        metricutils.increment(f'{metric_prefix}.failed')
        raise
    except Exception as e:
        logger.error('Unexpected error creating JSM support request', exc_info=True)
        metricutils.increment(f'{metric_prefix}.failed')
        raise JsmRequestException(original_error=e) from e


def create_jsm_request(subject: str, category: str, email: str, description: str,
                       attachments: Optional[List] = None) -> Optional[str]:
    """
    Create a JSM service desk request, raised on behalf of the submitter.

    :param subject: The submission's subject.
    :param category: The submission's category (e.g. ``Bug Report``).
    :param email: The submitter's email address, set as the request's reporter.
    :param description: The submission's description.
    :param attachments: Uploaded files to attach to the request.
    :return: The created request's issue key.
    :raises JsmRequestException: If the request could not be created.
    :raises JsmAttachmentException: If the request was created, but its attachments could not be uploaded.
    """
    return _create_request(_build_payload(subject, category, description, email),
                           attachments,
                           'action.support_contact',
                           f'from {redact_email(email)} ({category})')


def create_quarantined_jsm_request(subject: str, category: str, email: str, description: str, signals: List[str],
                                   attachments: Optional[List] = None) -> Optional[str]:
    """
    Create a JSM service desk request for suspected spam. It is raised on behalf of the support address,
    plus-addressed with ``+spam``, so the submitter receives no notifications and quarantined requests can
    be filtered by reporter. The submitter and matched signals are prepended to the description.

    :param subject: The submission's subject.
    :param category: The submission's category (e.g. ``Bug Report``).
    :param email: The submitter's email address.
    :param description: The submission's description.
    :param signals: The spam signals the submission matched.
    :param attachments: Uploaded files to attach to the request.
    :return: The created request's issue key.
    :raises JsmRequestException: If the request could not be created.
    :raises JsmAttachmentException: If the request was created, but its attachments could not be uploaded.
    """
    description = (f'Suspected spam (signals: {", ".join(signals)})\n'
                   f'Submitter: {email}\n'
                   f'----\n\n'
                   f'{description}')

    return _create_request(_build_payload(subject, category, description, _spam_reporter_email()),
                           attachments,
                           'action.support_contact.quarantine',
                           f'as suspected spam from {redact_email(email)} ({category}; signals={",".join(signals)})')
