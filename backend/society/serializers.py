from rest_framework import serializers
from .models import Society, Block, Flat, ResidentFlatMapping
from django.contrib.auth import get_user_model

User = get_user_model()


class SocietySerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Society
        fields = [
            'id', 'name', 'registration_number', 'address',
            'city', 'state', 'pincode',
            'contact_email', 'contact_phone',
            'admin', 'admin_name', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_admin_name(self, obj):
        if obj.admin:
            return obj.admin.get_full_name() or obj.admin.username
        return None


class BlockSerializer(serializers.ModelSerializer):
    society_name = serializers.ReadOnlyField(source='society.name')
    flat_count = serializers.SerializerMethodField()

    class Meta:
        model = Block
        fields = [
            'id', 'society', 'society_name', 'name',
            'total_floors', 'description', 'flat_count', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_flat_count(self, obj):
        return obj.flats.count()


class FlatSerializer(serializers.ModelSerializer):
    block_name = serializers.ReadOnlyField(source='block.name')
    society_name = serializers.ReadOnlyField(source='block.society.name')

    class Meta:
        model = Flat
        fields = [
            'id', 'block', 'block_name', 'society_name',
            'flat_number', 'floor', 'area_sqft',
            'is_occupied', 'created_at',
        ]
        read_only_fields = ['created_at', 'is_occupied']


class ResidentFlatMappingSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    user_email = serializers.ReadOnlyField(source='user.email')
    flat_number = serializers.ReadOnlyField(source='flat.flat_number')
    block_name = serializers.ReadOnlyField(source='flat.block.name')
    society_name = serializers.ReadOnlyField(source='flat.block.society.name')

    class Meta:
        model = ResidentFlatMapping
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'flat', 'flat_number', 'block_name', 'society_name',
            'occupancy_type', 'is_primary_resident',
            'move_in_date', 'move_out_date',
            'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def validate(self, data):
        # Ensure the same user is not mapped to the same flat twice
        user = data.get('user', getattr(self.instance, 'user', None))
        flat = data.get('flat', getattr(self.instance, 'flat', None))
        qs = ResidentFlatMapping.objects.filter(user=user, flat=flat)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'This resident is already mapped to this flat.'
            )
        return data
