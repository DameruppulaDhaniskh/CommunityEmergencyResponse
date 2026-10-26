from django.conf import settings
from django.db import models


class Incident(models.Model):
    EMERGENCY_TYPES = [
        ('medical', 'Medical Emergency'),
        ('fall', 'Fall / Injury'),
        ('fire', 'Fire'),
        ('security', 'Security Threat'),
        ('accident', 'Accident'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('ACTIVE_RESPONSE', 'Active Response'),
        ('ESCALATED', 'Escalated'),
        ('RESOLVED', 'Resolved'),
        ('CANCELLED', 'Cancelled'),
    ]

    resident = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incidents'
    )
    emergency_type = models.CharField(max_length=20, choices=EMERGENCY_TYPES)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_captured_at = models.DateTimeField(null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True, help_text='Metres')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def location_available(self):
        return self.latitude is not None and self.longitude is not None

    def __str__(self):
        return f"Incident #{self.pk} - {self.emergency_type} ({self.status})"