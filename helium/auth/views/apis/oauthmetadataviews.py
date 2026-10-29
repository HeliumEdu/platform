from django.conf import settings
from oauth2_provider.views import OAuthServerMetadataView


class HeliumOAuthServerMetadataView(OAuthServerMetadataView):
    """
    RFC 8414 authorization server metadata, with the app's consent screen as the authorization endpoint (it signs the
    user in, then completes the request through `OAuthAuthorizeView`).
    """

    def _get_endpoint_url(self, request, view_name, required=False):
        if view_name == 'authorize':
            return f'{settings.PROJECT_APP_HOST}/connect'
        return super()._get_endpoint_url(request, view_name, required)
