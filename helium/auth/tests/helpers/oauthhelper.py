import base64
import hashlib
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlparse

from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_application_model

REDIRECT_URI = 'https://claude.ai/api/mcp/auth_callback'
CODE_VERIFIER = 'a-code-verifier-that-is-long-enough-for-pkce-0123456789'


def code_challenge(verifier=CODE_VERIFIER):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode('ascii').rstrip('=')


def given_oauth_application_exists(name='Claude', redirect_uri=REDIRECT_URI):
    application_model = get_application_model()
    return application_model.objects.create(name=name,
                                            client_type=application_model.CLIENT_PUBLIC,
                                            authorization_grant_type=application_model.GRANT_AUTHORIZATION_CODE,
                                            redirect_uris=redirect_uri,
                                            skip_authorization=False)


def given_oauth_token_exists(user, application, scope='planner:read planner:import', token='opaque-oauth-token',
                             resource=None, expires_in=timedelta(hours=1)):
    return get_access_token_model().objects.create(user=user, application=application, token=token, scope=scope,
                                                   expires=timezone.now() + expires_in, resource=resource or [])


def authorization_query(client_id, **overrides):
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'planner:read planner:import',
        'state': 'xyz',
        'code_challenge': code_challenge(),
        'code_challenge_method': 'S256',
    }
    params.update(overrides)
    return urlencode({key: value for key, value in params.items() if value is not None}, doseq=True)


def redirect_params(redirect_uri):
    return {key: values[0] for key, values in parse_qs(urlparse(redirect_uri).query).items()}
