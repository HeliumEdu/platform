import logging
import uuid

from django.contrib.auth import get_user_model
from rest_framework import serializers

from helium.auth.serializers.userprofileserializer import UserProfileSerializer
from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.auth.tasks import send_verification_email
from helium.auth.utils.userutils import validate_password
from helium.importexport.tasks import import_example_schedule

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(help_text='A password to set for the user.',
                                     required=False, write_only=True)

    profile = UserProfileSerializer(required=False, read_only=True)

    settings = UserSettingsSerializer(required=False, read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'email_changing', 'password', 'profile', 'settings',)
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

    def validate_password(self, password):
        error = validate_password(password)

        if error:
            raise serializers.ValidationError(error)

        return password

    def update(self, instance, validated_data):
        # Manually process fields that require shuffling before relying on the serializer's internals to save the rest
        if 'email' in validated_data and instance.email != validated_data.get('email'):
            instance.email_changing = validated_data.pop('email')

            instance.verification_code = uuid.uuid4()

            send_verification_email.delay(instance.email_changing, instance.username, instance.verification_code)

        password = validated_data.pop('password', None)
        instance = super(UserSerializer, self).update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        return instance

    def create(self, validated_data):
        password = validated_data.pop('password')
        instance = super(UserSerializer, self).create(validated_data)

        instance.set_password(password)
        instance.save()

        send_verification_email.delay(instance.email, instance.username, instance.verification_code)

        # Import the example schedule for the user
        import_example_schedule.delay(instance.pk)

        return instance
