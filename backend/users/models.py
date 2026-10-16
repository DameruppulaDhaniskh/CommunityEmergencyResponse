from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds role, phone number, and flat/society fields.
    """
    ROLE_CHOICES = [
        ('resident', 'Resident'),
        ('guardian', 'Guardian'),
        ('volunteer', 'Volunteer'),
        ('security', 'Security Personnel'),
        ('admin', 'Society Admin'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='resident',
    )
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_image_url = models.URLField(null=True, blank=True)

    # Override email to make it unique and required
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
