"""
User serializer.
"""
import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            'username', 'email', 'email_changing', 'password',)
        read_only_fields = ('email',)
        extra_kwargs = {
            'email_changing': {'write_only': True},
            'password': {'write_only': True}
        }

    def validate_email_changing(self, value):
        """
        Ensure the email the user isn't already taken by another user.

        :param value: the new email address
        """
        if get_user_model().objects.filter(email=value).exists():
            raise serializers.ValidationError("Sorry, that email is already in use.")

        return value

    def update(self, instance, validated_data):
        if 'email_changing' in validated_data:
            # TODO: if the email is changing, send a new validation email
            pass
