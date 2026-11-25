import logging

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.core import exceptions
from django.db import IntegrityError, transaction
from django.utils.translation import gettext
from drf_spectacular.utils import extend_schema_field
from knox.models import AuthToken
from rest_framework import serializers
from rest_framework.fields import get_error_detail

from helium.auth.backends import OAuth2Authentication
from helium.auth.models import UserSettings
from helium.auth.serializers.useroauthproviderserializer import UserOAuthProviderSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.services.pushtokenservice import revoke_push_tokens
from helium.auth.tasks import send_verification_email
from helium.auth.utils.userutils import generate_verification_code, generate_unique_username_from_email, \
    is_admin_allowed_email
from helium.common import enums, errorcodes
from helium.common.errormessages import EMAIL_IN_USE_MESSAGE, REGISTRATION_RETRY_MESSAGE, admin_allowed_email_error
from helium.common.utils import taskutils

logger = logging.getLogger(__name__)

CONNECTED_APP_SETTINGS_ALLOWLIST = ('time_zone',)


class UserSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(
        help_text='The current password for the user (required when changing password or email).',
        required=False, write_only=True)

    password = serializers.CharField(help_text='A password to set for the user.',
                                     required=False, write_only=True)

    settings = UserSettingsSerializer(required=False, read_only=True)

    oauth_providers = UserOAuthProviderSerializer(many=True, read_only=True)

    has_usable_password = serializers.SerializerMethodField(
        help_text='Whether the user has a usable password (false for OAuth-only users).'
    )

    has_oauth_providers = serializers.SerializerMethodField(
        help_text='Whether the user has any OAuth providers linked.'
    )

    api_token_created_at = serializers.SerializerMethodField(
        help_text="When the user's API token was created, or null if they don't have one."
    )

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'email_changing', 'old_password', 'password',
                  'settings', 'oauth_providers', 'has_usable_password', 'has_oauth_providers',
                  'api_token_created_at',)
        read_only_fields = ('email_changing', 'oauth_providers', 'has_usable_password', 'has_oauth_providers',
                            'api_token_created_at',)
        extra_kwargs = {
            'email': {'validators': []},
        }

    def to_representation(self, instance):
        """
        A connected app (OAuth token) gets only the user's ``id``, ``email`` and the settings in
        ``CONNECTED_APP_SETTINGS_ALLOWLIST``, not how they sign in, whether they have an API token, or their private
        feed slug.
        """
        data = super().to_representation(instance)

        request = self.context.get('request')
        if request is not None and isinstance(getattr(request, 'successful_authenticator', None),
                                              OAuth2Authentication):
            return {
                'id': data['id'],
                'email': data['email'],
                'settings': {key: data['settings'][key] for key in CONNECTED_APP_SETTINGS_ALLOWLIST},
            }

        return data

    def get_has_usable_password(self, obj) -> bool:
        return obj.has_usable_password()

    def get_has_oauth_providers(self, obj) -> bool:
        return obj.oauth_providers.exists()

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_api_token_created_at(self, obj):
        created = AuthToken.objects.filter(user=obj).values_list('created', flat=True).first()
        return serializers.DateTimeField().to_representation(created) if created else None

    def validate(self, attrs):
        # If setting a password and user has a usable password, require old_password for security
        if 'password' in attrs and self.instance:
            if self.instance.has_usable_password() and 'old_password' not in attrs:
                raise serializers.ValidationError({
                    'old_password': gettext('Current password is required when changing your password.')
                }, code=errorcodes.OLD_PASSWORD_REQUIRED)

        # If changing email, require old_password for security
        if 'email' in attrs and self.instance and self.instance.email != attrs.get('email'):
            if 'old_password' not in attrs:
                raise serializers.ValidationError({
                    'old_password': gettext('Current password is required when changing your email.')
                }, code=errorcodes.OLD_PASSWORD_REQUIRED)

        return attrs

    def validate_email(self, email):
        """
        Ensure the email the user isn't already taken (or being changed to) by another user.

        :param email: the new email address
        """
        UserModel = get_user_model()

        if self.instance and self.instance.is_superuser and self.instance.email != email:
            if not is_admin_allowed_email(email):
                raise serializers.ValidationError(admin_allowed_email_error(),
                                                  code=errorcodes.ADMIN_EMAIL_DOMAIN_NOT_ALLOWED)

        if not self.instance:
            # A user pending deletion keeps their email reserved until the cascade finishes, so the
            # address is taken without an account the registrant could sign in to.
            if UserModel.objects.can_login().email_used(None, email):
                raise serializers.ValidationError(EMAIL_IN_USE_MESSAGE, code=errorcodes.EMAIL_IN_USE)
            elif UserModel.objects.email_used(None, email):
                raise serializers.ValidationError(REGISTRATION_RETRY_MESSAGE, code=errorcodes.REGISTRATION_RETRY)
        elif self.instance.email != email and UserModel.objects.email_used(self.instance.pk, email):
            raise serializers.ValidationError(EMAIL_IN_USE_MESSAGE, code=errorcodes.EMAIL_IN_USE)

        return email

    def validate_old_password(self, old_password):
        if self.instance and not self.instance.check_password(old_password):
            raise serializers.ValidationError(gettext('The current password was entered incorrectly and did not '
                                                      'match.'), code=errorcodes.OLD_PASSWORD_INCORRECT)

        return old_password

    def validate_password(self, password):
        UserModel = get_user_model()
        try:
            password_validation.validate_password(password=password, user=UserModel)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(get_error_detail(e))

        return password

    def update(self, instance, validated_data):
        # Manually process fields that require shuffling before relying on the serializer's internals to save the rest
        if 'email' in validated_data:
            new_email = validated_data.pop('email')
            if instance.email != new_email:
                # Initiate email change - requires verification
                instance.email_changing = new_email
                instance.verification_code = generate_verification_code()

                taskutils.safe_apply_async(send_verification_email,
                    args=(instance.email_changing, instance.verification_code),
                    kwargs={'clear_suppression': True},
                    critical=True,
                    priority=settings.CELERY_PRIORITY_HIGH,
                )
            elif instance.email_changing:
                # User submitted their existing email while a change is pending - cancel the change
                instance.email_changing = None
                instance.save()

        validated_data.pop('old_password', None)
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)

        if password:
            # For users with usable passwords, old_password is required (validated in validate())
            # For OAuth users without passwords, allow setting password directly to "upgrade" their account
            instance.set_password(password)
            instance.save()

            revoke_push_tokens([instance])

        return instance

    @staticmethod
    def sign_up_settings(data):
        """
        The settings a sign-up request reports for the new account.
        """
        return {field: data[field] for field in ('time_zone', 'language') if field in data}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user_settings = validated_data.pop('settings', {})
        validated_data['username'] = generate_unique_username_from_email(validated_data.get('email'))
        with transaction.atomic():
            try:
                with transaction.atomic():
                    instance = super().create(validated_data)
            except IntegrityError:
                raise serializers.ValidationError(EMAIL_IN_USE_MESSAGE, code=errorcodes.EMAIL_IN_USE)

            instance.set_password(password)
            instance.save()

            self._save_settings(instance, user_settings)

        taskutils.safe_apply_async(send_verification_email,
            args=(instance.email, instance.verification_code),
            kwargs={'clear_suppression': True},
            critical=True,
            priority=settings.CELERY_PRIORITY_HIGH,
        )

        return instance

    def create_from_oauth(self, validated_data):
        user_settings = validated_data.pop('settings', {})
        # OAuth users can bypass email verification
        validated_data['is_active'] = True

        with transaction.atomic():
            try:
                with transaction.atomic():
                    instance = super().create(validated_data)
            except IntegrityError:
                raise serializers.ValidationError(REGISTRATION_RETRY_MESSAGE, code=errorcodes.REGISTRATION_RETRY)

            # OAuth users bypass local passwords
            instance.set_unusable_password()
            instance.save()

            self._save_settings(instance, user_settings)

        return instance

    @staticmethod
    def _save_settings(instance, user_settings):
        if user_settings:
            settings_serializer = UserSettingsSerializer(instance.settings, data=user_settings, partial=True)
            settings_serializer.is_valid(raise_exception=True)
            settings_serializer.save()


class UserCreateSerializer(serializers.Serializer):
    email = serializers.CharField(help_text=get_user_model()._meta.get_field('email').help_text)

    password = serializers.CharField(help_text=get_user_model()._meta.get_field('password').help_text)

    time_zone = serializers.ChoiceField(choices=enums.TIME_ZONE_CHOICES,
                                        help_text=UserSettings._meta.get_field('time_zone').help_text)

    language = serializers.ChoiceField(choices=settings.LANGUAGES, required=False,
                                       help_text=UserSettings._meta.get_field('language').help_text)


class UserForgotSerializer(serializers.Serializer):
    email = serializers.CharField(help_text='The email for the user.')


class UserForgotConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(help_text='The base64-encoded user ID from the reset email link.')

    token = serializers.CharField(help_text='The password reset token from the reset email link.')

    password = serializers.CharField(help_text='The new password to set.')
