__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.core import exceptions
from django.db import IntegrityError
from rest_framework import serializers

from helium.auth.models import UserSettings
from helium.auth.serializers.useroauthproviderserializer import UserOAuthProviderSerializer
from helium.auth.serializers.userprofileserializer import UserProfileSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.tasks import send_verification_email
from helium.auth.utils.userutils import generate_verification_code, generate_unique_username_from_email, \
    is_admin_allowed_email
from helium.common import enums

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(
        help_text='The current password for the user (required when changing password or email).',
        required=False, write_only=True)

    password = serializers.CharField(help_text='A password to set for the user.',
                                     required=False, write_only=True)

    profile = UserProfileSerializer(required=False, read_only=True)

    settings = UserSettingsSerializer(required=False, read_only=True)

    oauth_providers = UserOAuthProviderSerializer(many=True, read_only=True)

    has_usable_password = serializers.SerializerMethodField(
        help_text='Whether the user has a usable password (false for OAuth-only users).'
    )

    has_oauth_providers = serializers.SerializerMethodField(
        help_text='Whether the user has any OAuth providers linked (Google, Apple, etc.).'
    )

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'email_changing', 'old_password', 'password',
                  'profile', 'settings', 'oauth_providers', 'has_usable_password', 'has_oauth_providers',)
        read_only_fields = ('email_changing', 'oauth_providers', 'has_usable_password', 'has_oauth_providers',)
        extra_kwargs = {
            'username': {'required': False, 'allow_blank': True},
        }

    def get_has_usable_password(self, obj) -> bool:
        """Return whether the user has a usable password."""
        return obj.has_usable_password()

    def get_has_oauth_providers(self, obj) -> bool:
        """Return whether the user has any OAuth providers linked."""
        return obj.oauth_providers.exists()

    def validate(self, attrs):
        email = attrs.get('email', self.instance.email if self.instance else None)
        username = attrs.get('username', self.instance.username if self.instance else None)

        if (username and username.startswith("heliumedu-cluster") and
                not (email.endswith("heliumedu.dev") or email.endswith("heliumedu.com"))):
            raise serializers.ValidationError("Sorry, this username is reserved for Helium staff.")

        # If setting a password and user has a usable password, require old_password for security
        if 'password' in attrs and self.instance:
            if self.instance.has_usable_password() and 'old_password' not in attrs:
                raise serializers.ValidationError({
                    'old_password': 'Current password is required when changing your password.'
                })

        # If changing email, require old_password for security
        if 'email' in attrs and self.instance and self.instance.email != attrs.get('email'):
            if 'old_password' not in attrs:
                raise serializers.ValidationError({
                    'old_password': 'Current password is required when changing your email.'
                })

        return attrs

    def validate_email(self, email):
        """
        Ensure the email the user isn't already taken (or being changed to) by another user.

        :param email: the new email address
        """
        if self.instance and self.instance.is_superuser and self.instance.email != email:
            if not is_admin_allowed_email(email):
                raise serializers.ValidationError(
                    f"Admin email must be within an allowed domain ({', '.join(settings.ADMIN_ALLOWED_DOMAINS)}).")

        if self.instance and self.instance.email != email and get_user_model().objects.email_used(self.instance.pk,
                                                                                                  email):
            raise serializers.ValidationError("Sorry, that email is already in use.")

        return email

    def validate_old_password(self, old_password):
        if self.instance and not self.instance.check_password(old_password):
            raise serializers.ValidationError("The current password was entered incorrectly and did not match.")

        return old_password

    def validate_password(self, password):
        try:
            password_validation.validate_password(password=password, user=get_user_model())
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return password

    def update(self, instance, validated_data):
        # Manually process fields that require shuffling before relying on the serializer's internals to save the rest
        if 'email' in validated_data:
            new_email = validated_data.pop('email')
            if instance.email != new_email:
                # Initiate email change - requires verification
                instance.email_changing = new_email
                instance.verification_code = generate_verification_code()

                send_verification_email.apply_async(
                    args=(instance.email_changing, instance.username, instance.verification_code),
                    priority=settings.CELERY_PRIORITY_HIGH,
                )
            elif instance.email_changing:
                # User submitted their existing email while a change is pending - cancel the change
                instance.email_changing = None
                instance.save()

        old_password = validated_data.pop('old_password', None)
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)

        if password:
            # For users with usable passwords, old_password is required (validated in validate())
            # For OAuth users without passwords, allow setting password directly to "upgrade" their account
            instance.set_password(password)
            instance.save()

        return instance

    def create(self, validated_data):
        password = validated_data.pop('password')
        username = validated_data.get('username')
        if not username:
            validated_data['username'] = generate_unique_username_from_email(
                validated_data.get('email')
            )
        try:
            instance = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError('Registration failed due to a conflict. Please try again.')

        instance.set_password(password)
        instance.save()

        send_verification_email.apply_async(
            args=(instance.email, instance.username, instance.verification_code),
            priority=settings.CELERY_PRIORITY_HIGH,
        )

        return instance

    def create_from_oauth(self, validated_data):
        # OAuth users can bypass email verification
        validated_data['is_active'] = True

        instance = super().create(validated_data)

        # OAuth users bypass local passwords
        instance.set_unusable_password()
        instance.save()

        return instance


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=get_user_model()._meta.get_field('username').help_text
    )

    email = serializers.CharField(help_text=get_user_model()._meta.get_field('email').help_text)

    password = serializers.CharField(help_text=get_user_model()._meta.get_field('password').help_text)

    time_zone = serializers.ChoiceField(choices=enums.TIME_ZONE_CHOICES,
                                        help_text=UserSettings._meta.get_field('time_zone').help_text)


class UserVerifySerializer(serializers.Serializer):
    username = serializers.CharField(help_text='The username for the user.')

    code = serializers.CharField(help_text=get_user_model()._meta.get_field('verification_code').help_text)


class UserForgotSerializer(serializers.Serializer):
    email = serializers.CharField(help_text='The email for the user.')
