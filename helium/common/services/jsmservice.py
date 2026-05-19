__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import base64
import json
import logging
import mimetypes
import urllib.error
import urllib.request
import uuid

from django.conf import settings

from helium.common.utils import metricutils
from helium.common.utils.commonutils import HeliumError, clear_ses_suppression_if_exists, redact_email

logger = logging.getLogger(__name__)

JSM_REQUEST_TIMEOUT_SECONDS = 15


class JsmRequestException(HeliumError):
    """Raised when a JSM service desk request cannot be created or an attachment cannot be uploaded."""

    def __init__(self, message='Failed to create JSM service desk request', original_error=None):
        self.original_error = original_error
        super().__init__(message)


def _auth_header():
    """
    Build the HTTP Basic auth header for the JSM service account from the configured
    account email and API token.
    """
    raw = f'{settings.JSM_SERVICE_ACCOUNT_EMAIL}:{settings.JSM_API_TOKEN}'
    encoded = base64.b64encode(raw.encode('utf-8')).decode('ascii')
    return f'Basic {encoded}'


def _request_type_id_for(category):
    """
    Resolve the JSM request type id for a submitted support category, falling back to the
    configured default request type when the category is unmapped.

    :param category: The validated support category label (e.g. ``Bug Report``).
    :return: The JSM request type id as a string.
    """
    return settings.JSM_REQUEST_TYPE_ID_MAP.get(category, settings.JSM_REQUEST_TYPE_ID)


def _open(request):
    """
    Execute a prepared ``urllib`` request against JSM, returning the decoded JSON body.

    :param request: A prepared :class:`urllib.request.Request`.
    :return: The parsed JSON response body, or ``None`` when the response carries no body.
    :raises JsmRequestException: On any HTTP error or transport failure.
    """
    try:
        with urllib.request.urlopen(request, timeout=JSM_REQUEST_TIMEOUT_SECONDS) as response:
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
    """
    POST a JSON body to a JSM servicedeskapi path and return the parsed response.

    :param path: The servicedeskapi path (e.g. ``/rest/servicedeskapi/request``).
    :param payload: The request body, serialized to JSON.
    :return: The parsed JSON response body.
    """
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
    """
    Upload a single file to the service desk's temporary attachment store.

    Two-step JSM attachment flow, step one: ``POST servicedeskapi/servicedesk/{id}/attachTemporaryFile``
    with a multipart body. JSM returns opaque temporary attachment ids that are then bound to a
    request in :func:`_attach_to_request`.

    :param uploaded_file: A Django ``UploadedFile``-like object.
    :return: The list of temporary attachment id strings returned by JSM.
    """
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
    """
    Bind previously-uploaded temporary attachments to a created request.

    Two-step JSM attachment flow, step two: ``POST servicedeskapi/request/{key}/attachment``.

    :param issue_key: The created request's issue key (e.g. ``HS-123``).
    :param temporary_attachment_ids: Temporary attachment ids from :func:`_attach_temporary_file`.
    """
    # TODO(verify-against-live-HS): confirm the attachment payload field names
    #  (temporaryAttachmentIds, public) against the live HS instance.
    payload = {
        'temporaryAttachmentIds': temporary_attachment_ids,
        'public': True,
    }
    _post_json(f'/rest/servicedeskapi/request/{issue_key}/attachment', payload)


def create_jsm_request(subject, category, email, description, attachments=None):
    """
    Create a JSM service desk request on behalf of the submitter via the authenticated
    JSM Cloud REST API. ``raiseOnBehalfOf`` sets the submitter as the request reporter.

    :param subject: User-supplied subject line.
    :param category: Validated category label (e.g. ``Bug Report``).
    :param email: Validated submitter email address; set as the request reporter.
    :param description: Free-form body content.
    :param attachments: Iterable of uploaded files (Django ``UploadedFile``-like).
    :raises JsmRequestException: If the request or any attachment upload fails.
    """
    clear_ses_suppression_if_exists(email)

    request_type_id = _request_type_id_for(category)

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

    payload = {
        'serviceDeskId': str(settings.JSM_SERVICE_DESK_ID),
        'requestTypeId': str(request_type_id),
        'raiseOnBehalfOf': email,
        'requestFieldValues': request_field_values,
    }

    try:
        response = _post_json('/rest/servicedeskapi/request', payload)
        issue_key = (response or {}).get('issueKey')

        attachments = list(attachments or [])
        if attachments:
            if not issue_key:
                logger.warning('JSM request created without an issueKey; skipping attachments')
            else:
                temporary_attachment_ids = []
                for f in attachments:
                    temporary_attachment_ids.extend(_attach_temporary_file(f))
                if temporary_attachment_ids:
                    _attach_to_request(issue_key, temporary_attachment_ids)

        metricutils.increment('action.support_contact.sent')
        logger.info(
            f'Support contact created in JSM ({issue_key or "unknown"}) '
            f'from {redact_email(email)} ({category})'
        )
        return issue_key
    except JsmRequestException:
        metricutils.increment('action.support_contact.failed')
        raise
    except Exception as e:
        logger.error('Unexpected error creating JSM support request', exc_info=True)
        metricutils.increment('action.support_contact.failed')
        raise JsmRequestException(original_error=e) from e
