from django.db import models
from django.conf import settings
import secrets


class EmergencyContact(models.Model):
    """
    An emergency contact configured by a resident.
    Supports primary/secondary guardian designation and general contacts.
    """
    CONTACT_TYPES = [
        ('primary_guardian', 'Primary Guardian'),
        ('secondary_guardian', 'Secondary Guardian'),
        ('emergency_contact', 'Emergency Contact'),
    ]

    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('child', 'Child'),
        ('relative', 'Relative'),
        ('friend', 'Friend'),
        ('neighbor', 'Neighbor'),
        ('colleague', 'Colleague'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ]

    # The resident who owns this contact entry
    resident = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emergency_contacts',
    )

    # If the contact is also a registered user in the platform
    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_as_contact',
    )

    contact_type = models.CharField(
        max_length=25,
        choices=CONTACT_TYPES,
        default='emergency_contact',
    )
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        default='other',
    )

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Priority order for notification routing (lower = higher priority)
    priority = models.PositiveIntegerField(default=1)

    # Contact verification
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['resident', 'priority']
        constraints = [
            # Only one primary guardian per resident
            models.UniqueConstraint(
                fields=['resident', 'contact_type'],
                condition=models.Q(contact_type='primary_guardian'),
                name='unique_primary_guardian_per_resident',
            ),
            # Only one secondary guardian per resident
            models.UniqueConstraint(
                fields=['resident', 'contact_type'],
                condition=models.Q(contact_type='secondary_guardian'),
                name='unique_secondary_guardian_per_resident',
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} ({self.get_contact_type_display()}) "
            f"← {self.resident.username}"
        )

    def generate_verification_token(self):
        """Generate a secure random token for contact verification."""
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token
