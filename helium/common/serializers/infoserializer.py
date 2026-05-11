__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class InfoSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='The name of the API service.')

    tagline = serializers.CharField(help_text='Tagline for the service.')

    version = serializers.CharField(help_text='The deployed API version.')

    support_email = serializers.EmailField(help_text='Email address for support inquiries.')

    max_upload_size = serializers.IntegerField(
        help_text='Maximum size, in bytes, for any single file upload (attachments and imports).'
    )

    access_token_lifetime_minutes = serializers.IntegerField(
        help_text='Lifetime, in minutes, of an `access` token issued by `/auth/token/`. '
                  'Clients should refresh before this expires.'
    )


    refresh_token_lifetime_days = serializers.IntegerField(
        help_text='Lifetime, in days, of a `refresh` token issued by `/auth/token/`. '
                  'Once expired, the user must log in again.'
    )

    oauth_providers = serializers.ListField(
        child=serializers.CharField(),
        help_text='OAuth providers accepted by `/auth/oauth/login/`.'
    )

    import_file_types = serializers.ListField(
        child=serializers.CharField(),
        help_text='File extensions accepted by `/importexport/import/`.'
    )
