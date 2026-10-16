from rest_framework import serializers
from .models import EmergencyContact


class EmergencyContactSerializer(serializers.ModelSerializer):
    resident_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'resident', 'resident_name',
            'linked_user',
            'contact_type', 'relationship',
            'name', 'phone', 'email', 'address',
            'priority',
            'is_verified', 'verified_at',
            'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'resident', 'is_verified', 'verified_at',
            'created_at', 'updated_at',
        ]

    def get_resident_name(self, obj):
        return obj.resident.get_full_name() or obj.resident.username

    def validate(self, data):
        request = self.context.get('request')
        contact_type = data.get('contact_type', getattr(self.instance, 'contact_type', None))

        # Enforce unique primary / secondary guardian per resident
        if contact_type in ('primary_guardian', 'secondary_guardian'):
            qs = EmergencyContact.objects.filter(
                resident=request.user,
                contact_type=contact_type,
                is_active=True,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                label = dict(EmergencyContact.CONTACT_TYPES)[contact_type]
                raise serializers.ValidationError(
                    {
                        'contact_type': (
                            f'You already have a {label} configured. '
                            'Update the existing one instead.'
                        )
                    }
                )
        return data


class ContactVerificationSerializer(serializers.Serializer):
    """Used when a contact clicks the verification link."""
    token = serializers.CharField(required=True)
