import logging
import uuid

from django.contrib.auth import get_user_model
from rest_framework import serializers

from helium.auth import tasks
from helium.auth.serializers.userprofileserializer import UserProfileSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False, read_only=True)

    settings = UserSettingsSerializer(required=False, read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'email_changing', 'verification_code', 'profile', 'settings',)
        read_only_fields = ('email_changing',)
        extra_kwargs = {
            'verification_code': {'write_only': True},
        }

    def validate_email(self, email):
        """
        Ensure the email the user isn't already taken (or being changed to) by another user.

        :param email: the new email address
        """
        if self.instance.email != email and get_user_model().objects.email_used(self.instance.pk, email):
            raise serializers.ValidationError("Sorry, that email is already in use.")

        return email

    def update(self, instance, validated_data):
        # Manually process fields that require shuffling before relying on the serializer's internals to save the rest
        if 'email' in validated_data and instance.email != validated_data.get('email'):
            instance.email_changing = validated_data.pop('email')

            instance.verification_code = uuid.uuid4()

            tasks.send_verification_email.delay(instance.email_changing, instance.username, instance.verification_code)

        instance = super(UserSerializer, self).update(instance, validated_data)

        return instance
