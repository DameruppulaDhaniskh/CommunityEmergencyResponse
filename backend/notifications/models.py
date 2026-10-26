from django.conf import settings
from django.db import models


class Notification(models.Model):
    RECIPIENT_TYPES = [
        ('primary_guardian', 'Primary Guardian'),
        ('security', 'Security'),
        ('volunteer', 'Volunteer'),
        ('community', 'Community'),
    ]
    CHANNELS = [
        ('push', 'Push'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('in_app', 'In-App'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    ]

    incident = models.ForeignKey(
        'incidents.Incident', on_delete=models.CASCADE, related_name='notifications'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications',
    )
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES)
    recipient_name = models.CharField(max_length=100, blank=True)
    recipient_phone = models.CharField(max_length=15, blank=True)
    recipient_email = models.EmailField(blank=True)
    channel = models.CharField(max_length=10, choices=CHANNELS)

    title = models.CharField(max_length=200)
    message = models.TextField()

    # Delivery tracking (separate from read status)
    delivery_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    provider_message_id = models.CharField(max_length=100, blank=True)
    is_simulated = models.BooleanField(default=False)
    failure_reason = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    # Read tracking (in-app only; reading is NOT delivery or acknowledgment)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Prevents duplicate notifications for the same recipient + channel
    dedupe_key = models.CharField(max_length=150)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['incident', 'dedupe_key'],
                name='unique_notification_per_recipient_channel',
            ),
        ]

    def __str__(self):
        return f"{self.channel} -> {self.recipient_name} ({self.delivery_status})"