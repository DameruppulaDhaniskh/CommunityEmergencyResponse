from django.db import models
from django.conf import settings


class Society(models.Model):
    """Represents a residential society / apartment complex."""
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='administered_societies',
        limit_choices_to={'role': 'admin'},
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Societies'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"


class Block(models.Model):
    """
    A block or tower within a society.
    E.g.: Block A, Tower 1, Wing C.
    """
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='blocks',
    )
    name = models.CharField(max_length=100)  # e.g. "Block A", "Tower 1"
    total_floors = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('society', 'name')
        ordering = ['society', 'name']

    def __str__(self):
        return f"{self.name} — {self.society.name}"


class Flat(models.Model):
    """
    A flat/unit within a block.
    E.g.: Flat 101 on Floor 1 of Block A.
    """
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name='flats',
    )
    flat_number = models.CharField(max_length=20)  # e.g. "101", "G-02"
    floor = models.IntegerField(default=0)          # 0 = Ground
    area_sqft = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('block', 'flat_number')
        ordering = ['block', 'floor', 'flat_number']

    def __str__(self):
        return f"Flat {self.flat_number}, {self.block}"


class ResidentFlatMapping(models.Model):
    """
    Maps a resident (User) to a flat in a society.
    Supports owner / tenant distinction and tracks move-in/out dates.
    """
    OCCUPANCY_TYPES = [
        ('owner', 'Owner'),
        ('tenant', 'Tenant'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flat_mappings',
    )
    flat = models.ForeignKey(
        Flat,
        on_delete=models.CASCADE,
        related_name='residents',
    )
    occupancy_type = models.CharField(
        max_length=10,
        choices=OCCUPANCY_TYPES,
        default='tenant',
    )
    is_primary_resident = models.BooleanField(default=True)
    move_in_date = models.DateField(null=True, blank=True)
    move_out_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'flat')
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user} → Flat {self.flat.flat_number}"
            f" ({self.occupancy_type})"
        )
