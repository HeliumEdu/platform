import logging

from django.conf import settings
from django.utils import timezone
from oauth2_provider.exceptions import FatalClientError, OAuthToolkitError
from oauth2_provider.models import (
    get_access_token_model,
    get_application_model,
    get_refresh_token_model,
)
from oauth2_provider.oauth2_backends import get_oauthlib_core
from oauth2_provider.scopes import get_scopes_backend
from oauth2_provider.settings import oauth2_settings
from oauthlib.common import add_params_to_uri
from oauthlib.oauth2.rfc6749.errors import CustomOAuth2Error
from rest_framework.exceptions import ValidationError

from helium.auth.models import UserClientActivity
from helium.auth.utils.userutils import mark_user_active
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)

#: The endpoints each OAuth scope reaches, as (URL name, method). OAuth tokens are refused everywhere else, so a new
#: endpoint is never reachable with one until it's listed here.
OAUTH_SCOPE_ENDPOINTS = {
    'planner:read': {
        ('auth_user_detail', 'GET'),
        ('planner_coursegroups_list', 'GET'),
        ('planner_courses_list', 'GET'),
        ('planner_courseschedules_list', 'GET'),
        ('planner_categories_list', 'GET'),
        ('planner_homework_list', 'GET'),
        ('planner_events_list', 'GET'),
        ('planner_resource_grades', 'GET'),
        ('planner_notes_list', 'GET'),
        ('planner_resourcegroups_list', 'GET'),
        ('planner_resources_list', 'GET'),
    },
    'planner:import': {
        ('auth_user_detail', 'GET'),
        ('planner_coursegroups_list', 'GET'),
        ('importexport_import', 'POST'),
    },
}


def allows_helium_resource(audience_uri, audiences) -> bool:
    """
    Accept a token bound to one of Helium's own resources wherever on the API it's presented: a connector forwards
    the token it was issued to the API behind it. Used as `RESOURCE_SERVER_TOKEN_RESOURCE_VALIDATOR`.

    :param audience_uri: the URI the token is presented at.
    :param audiences: the resources the token is bound to.
    :return: whether the token is accepted.
    """
    return any(_normalize(audience) in _helium_resources() for audience in audiences)


def scope_allows(token, url_name, method) -> bool:
    """
    Whether an OAuth token's scopes reach an endpoint.

    :param token: the OAuth access token.
    :param url_name: the name of the URL being requested.
    :param method: the HTTP method of the request.
    :return: whether any of the token's scopes allows the endpoint.
    """
    return any((url_name, method) in OAUTH_SCOPE_ENDPOINTS.get(scope, ()) for scope in token.scope.split())


def describe_authorization(request) -> dict:
    """
    Validate an authorization request (its parameters are in the request's query string) and describe what it asks
    for, so the user can consent.

    :param request: the current django.http.HttpRequest, with the OAuth parameters in its query string.
    :return: the client's name, where it redirects, and the requested scopes with their descriptions.
    :raises ValidationError: when the request is invalid. When the client may be told, `redirect_uri` is the error
        redirect to send the user to.
    """
    try:
        scopes, credentials = get_oauthlib_core().validate_authorization_request(request)
        _require_s256(credentials)
        _requested_resources(request, credentials)
    except OAuthToolkitError as error:
        raise _authorization_error(error, request)

    application = get_application_model().objects.get(client_id=credentials['client_id'])
    descriptions = get_scopes_backend().get_all_scopes()

    return {
        'client_name': application.name,
        'redirect_uri': credentials['redirect_uri'],
        'scopes': [{'scope': scope, 'description': descriptions[scope]} for scope in scopes],
    }


def connected_apps(user) -> list[dict]:
    """
    The apps the user has granted access to that can still act for them (a refresh token not yet revoked, or an
    access token not yet expired), most recently used first.

    :param user: the user.
    :return: each app's id, name, the scopes its latest token holds, and when it last obtained a token.
    """
    live = set(get_refresh_token_model().objects.filter(user=user, revoked__isnull=True)
               .values_list('application_id', flat=True))
    live |= set(get_access_token_model().objects.filter(user=user, expires__gt=timezone.now())
                .values_list('application_id', flat=True))

    latest = {}
    for token in get_access_token_model().objects.filter(user=user, application_id__in=live).order_by('created'):
        latest[token.application_id] = token

    descriptions = get_scopes_backend().get_all_scopes()
    apps = []
    for application in get_application_model().objects.filter(pk__in=live):
        token = latest.get(application.pk)
        apps.append({
            'id': application.pk,
            'name': application.name,
            'scopes': [{'scope': scope, 'description': descriptions.get(scope, scope)}
                       for scope in (token.scope.split() if token else [])],
            'last_used_at': token.created if token else None,
        })
    return sorted(apps, key=lambda app: app['last_used_at'] or timezone.now(), reverse=True)


def decide_authorization(request, allow) -> str:
    """
    Complete an authorization request as the user decided: issue an authorization code to the client, or tell it
    access was denied.

    :param request: the current django.http.HttpRequest, with the OAuth parameters in its query string and the
        consenting user as `request.user`.
    :param allow: whether the user approved.
    :return: the URL to send the user to, back at the client.
    :raises ValidationError: when the request is invalid. When the client may be told, `redirect_uri` is the error
        redirect to send the user to.
    """
    core = get_oauthlib_core()
    try:
        scopes, credentials = core.validate_authorization_request(request)
        resources = _requested_resources(request, credentials)
        if resources:
            credentials['resource'] = resources

        uri, _, _, _ = core.create_authorization_response(request, scopes=scopes, credentials=credentials,
                                                          allow=allow)
    except FatalClientError as error:
        raise _authorization_error(error, request)
    except OAuthToolkitError as error:
        if allow or error.oauthlib_error.error != 'access_denied':
            raise _authorization_error(error, request)
        logger.info(f'OAuth authorization denied by user {request.user.pk}')
        metricutils.increment('action.oauth.denied', user=request.user)
        error.oauthlib_error.description = 'The user denied access.'
        return _error_redirect(error, request)

    logger.info(f'OAuth authorization granted by user {request.user.pk} to client {credentials["client_id"]}')
    metricutils.increment('action.oauth.authorized', user=request.user)

    return uri


def record_token_issued(token, request) -> None:
    """
    Count a user's connector use as activity: issuing or refreshing a token keeps the account from going dormant,
    the same as signing in to the app.

    :param token: the issued access token.
    :param request: the token request.
    """
    user = token.user
    if user is None:
        return

    mark_user_active(user)

    UserClientActivity.objects.get_or_create(user=user, date=timezone.now().date(),
                                             client=UserClientActivity.CLIENT_CONNECTOR)


def _require_s256(credentials) -> None:
    # Issuing the code refuses "plain" PKCE (COMPLIANT_BCP_RFC9700_PKCE_METHOD); refuse it before the user consents
    if credentials.get('code_challenge_method') != 'S256':
        raise OAuthToolkitError(
            error=CustomOAuth2Error(error='invalid_request',
                                    description='Unsupported code_challenge_method; use "S256".',
                                    state=credentials.get('state')),
            redirect_uri=credentials['redirect_uri'])


def _requested_resources(request, credentials) -> list[str]:
    resources = request.GET.getlist('resource')
    for resource in resources:
        if _normalize(resource) not in _helium_resources():
            raise OAuthToolkitError(
                error=CustomOAuth2Error(error='invalid_target',
                                        description=f"The resource '{resource}' isn't one Helium issues tokens for.",
                                        state=credentials.get('state')),
                redirect_uri=credentials['redirect_uri'])
    return resources


def _authorization_error(error, request) -> ValidationError:
    oauthlib_error = error.oauthlib_error
    detail = {'error': oauthlib_error.error, 'error_description': oauthlib_error.description}
    if not isinstance(error, FatalClientError) and oauthlib_error.redirect_uri:
        detail['redirect_uri'] = _error_redirect(error, request)
    return ValidationError(detail)


def _error_redirect(error, request) -> str:
    oauthlib_error = error.oauthlib_error
    params = oauthlib_error.twotuples
    if oauth2_settings.COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS:
        # RFC 9207: error responses carry the issuer too, as DOT adds it to successful ones
        params.append(('iss', oauth2_settings.oauth2_authorization_server_issuer(request)))
    return add_params_to_uri(oauthlib_error.redirect_uri, params)


def _helium_resources() -> set[str]:
    return {_normalize(resource) for resource in (*settings.OAUTH_CONNECTOR_RESOURCES, settings.PROJECT_API_HOST)}


def _normalize(uri) -> str:
    return uri.rstrip('/')
