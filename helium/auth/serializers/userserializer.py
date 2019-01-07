import logging
import uuid

from django.contrib.auth import get_user_model, password_validation
from django.core import exceptions
from rest_framework import serializers

from helium.auth.serializers.userprofileserializer import UserProfileSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.tasks import send_verification_email
from helium.importexport.tasks import import_example_schedule

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(
        help_text='The current password for the user (required only when changing an existing password).',
        required=False, write_only=True)

    password = serializers.CharField(help_text='A password to set for the user.',
                                     required=False, write_only=True)

    profile = UserProfileSerializer(required=False, read_only=True)

    settings = UserSettingsSerializer(required=False, read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'email_changing', 'old_password', 'password', 'profile', 'settings',)
        read_only_fields = ('email_changing',)

    def validate_email(self, email):
        """
        Ensure the email the user isn't already taken (or being changed to) by another user.

        :param email: the new email address
        """
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
        if 'email' in validated_data and instance.email != validated_data.get('email'):
            instance.email_changing = validated_data.pop('email')

            instance.verification_code = uuid.uuid4()

            send_verification_email.delay(instance.email_changing, instance.username, instance.verification_code)

        old_password = validated_data.pop('old_password', None)
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)

        if old_password and password:
            instance.set_password(password)
            instance.save()

        return instance

    def create(self, validated_data):
        password = validated_data.pop('password')
        instance = super().create(validated_data)

        instance.set_password(password)
        instance.save()

        send_verification_email.delay(instance.email, instance.username, instance.verification_code)

        # Import the example schedule for the user
        import_example_schedule.delay(instance.pk)

        return instance
