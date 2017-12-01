"""
UserProfile serializer.
"""
import logging

from rest_framework import serializers

from helium.users import tasks
from helium.users.models import UserProfile
from helium.users.utils.userutils import generate_phone_verification_code

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            'phone', 'phone_changing', 'phone_carrier', 'phone_carrier_changing', 'phone_verification_code')
        read_only_fields = ('phone_changing', 'phone_carrier_changing')
        extra_kwargs = {
            'phone_verification_code': {'write_only': True},
        }

    def validate(self, attrs):
        """
        Neither phone nor phone_carrier are required fields, but if one is set, the other must be also.

        :param attrs: the data to be saved
        :return: the validated data
        """
        if 'phone' in attrs and 'phone_carrier' not in attrs or 'phone_carrier' in attrs and 'phone' not in attrs:
            raise serializers.ValidationError("If one of 'phone' or 'phone_carrier' is provided, both are required")

        return attrs

    def validate_phone_verification_code(self, value):
        """
        Ensure the email the user isn't already taken by another user.

        :param value: the new email address
        """
        if value != self.instance.phone_verification_code:
            raise serializers.ValidationError("The verification code does not match our records")

        return value

    def update(self, instance, validated_data):

        if 'phone_verification_code' in validated_data:
            if instance.phone_changing:
                instance.phone = instance.phone_changing
                instance.phone_changing = None

            if instance.phone_carrier_changing:
                instance.phone_carrier = instance.phone_carrier_changing
                instance.phone_carrier_changing = None
        elif 'phone' in validated_data and 'phone_carrier' in validated_data:
            instance.phone_changing = validated_data.get('phone')
            instance.phone_carrier_changing = validated_data.get('phone_carrier')

            instance.phone_verification_code = generate_phone_verification_code()

            tasks.send_verification_text.delay(instance.phone_changing, instance.phone_carrier_changing, instance.phone_verification_code)

        instance.save()

        return instance
