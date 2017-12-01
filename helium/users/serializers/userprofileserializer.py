"""
UserProfile serializer.
"""
import logging

from rest_framework import serializers

from helium.users.models import UserProfile

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            'phone', 'phone_changing', 'phone_carrier', 'phone_carrier_changing',)
        read_only_fields = ('phone', 'phone_carrier')
        extra_kwargs = {
            'phone_changing': {'write_only': True},
            'phone_carrier_changing': {'write_only': True}
        }

    def is_valid(self, raise_exception=False):
        super(UserProfileSerializer, self).is_valid(raise_exception)

        print self.fields.get('phone_changing')
        # TODO: validate additional constraints

    def update(self, instance, validated_data):
        if 'phone_changing' in validated_data or 'phone_carrier_changing' in validated_data:
            # TODO: if the phone or carrier is changing, send a new validation text
            pass
