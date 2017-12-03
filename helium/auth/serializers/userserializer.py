"""
User serializer.
"""
import logging
import uuid

from django.contrib.auth import get_user_model
from rest_framework import serializers

from helium.auth import tasks

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'email_changing', 'verification_code')
        read_only_fields = ('email_changing',)
        extra_kwargs = {
            'verification_code': {'write_only': True},
        }

    def validate_email(self, email):
        """
        Ensure the email the user isn't already taken (or being changed to) by another user.

        :param email: the new email address
        """
        if get_user_model().objects.filter(email_changing=email).exists():
            raise serializers.ValidationError("This email is already in use.")

        return email

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username')

        if 'email' in validated_data and instance.email != validated_data.get('email'):
            instance.email_changing = validated_data.get('email')

            instance.verification_code = uuid.uuid4

            tasks.send_verification_email.delay(instance.email_changing, instance.username, instance.verification_code,
                                                self.context['request'].get_host())

        instance.save()

        return instance
