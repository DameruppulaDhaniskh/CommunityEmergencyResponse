from django.contrib import admin
from .models import EmergencyContact


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'resident', 'contact_type', 'relationship',
        'phone', 'is_verified', 'is_active',
    )
    list_filter = ('contact_type', 'relationship', 'is_verified', 'is_active')
    search_fields = ('name', 'phone', 'email', 'resident__email')
    readonly_fields = ('verification_token', 'verification_sent_at', 'verified_at')
