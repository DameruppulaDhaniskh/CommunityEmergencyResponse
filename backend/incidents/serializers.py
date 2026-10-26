from django.utils import timezone
from rest_framework import serializers

from .models import Incident


class IncidentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            'emergency_type', 'description', 'latitude', 'longitude',
            'location_captured_at', 'location_accuracy',
        ]

    def validate(self, attrs):
        lat = attrs.get('latitude')
        lng = attrs.get('longitude')
        if (lat is None) != (lng is None):
            raise serializers.ValidationError(
                'Provide both latitude and longitude, or neither.'
            )
        if lat is not None:
            if not -90 <= lat <= 90:
                raise serializers.ValidationError({'latitude': 'Must be between -90 and 90.'})
            if not -180 <= lng <= 180:
                raise serializers.ValidationError({'longitude': 'Must be between -180 and 180.'})
            if not attrs.get('location_captured_at'):
                attrs['location_captured_at'] = timezone.now()
        return attrs


class IncidentSerializer(serializers.ModelSerializer):
    location_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'resident', 'emergency_type', 'description',
            'latitude', 'longitude', 'location_available',
            'location_captured_at', 'location_accuracy',
            'status', 'created_at', 'updated_at', 'resolved_at',
        ]
        read_only_fields = fields


class IncidentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = ['id', 'status', 'updated_at', 'resolved_at']
        read_only_fields = fields