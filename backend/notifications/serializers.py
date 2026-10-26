from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """What a recipient sees about their own notification."""

    class Meta:
        model = Notification
        fields = [
            'id', 'incident', 'recipient_type', 'channel', 'title', 'message',
            'delivery_status', 'is_simulated', 'is_read', 'read_at',
            'created_at', 'sent_at', 'delivered_at',
        ]
        read_only_fields = fields


class NotificationRecordSerializer(serializers.ModelSerializer):
    """What authorized staff see when monitoring an incident (no message text, phone or email)."""

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient_name', 'recipient_type', 'channel',
            'delivery_status', 'is_simulated', 'provider_message_id',
            'failure_reason', 'attempt_count', 'last_attempt_at',
            'is_read', 'read_at', 'created_at', 'sent_at', 'delivered_at',
        ]
        read_only_fields = fields