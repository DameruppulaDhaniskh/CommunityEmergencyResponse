from django.contrib import admin
from .models import Society, Block, Flat, ResidentFlatMapping


@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'city', 'state', 'is_active')
    list_filter = ('city', 'state', 'is_active')
    search_fields = ('name', 'registration_number', 'city')


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('name', 'society', 'total_floors')
    list_filter = ('society',)
    search_fields = ('name', 'society__name')


@admin.register(Flat)
class FlatAdmin(admin.ModelAdmin):
    list_display = ('flat_number', 'block', 'floor', 'is_occupied')
    list_filter = ('block__society', 'is_occupied')
    search_fields = ('flat_number', 'block__name')


@admin.register(ResidentFlatMapping)
class ResidentFlatMappingAdmin(admin.ModelAdmin):
    list_display = ('user', 'flat', 'occupancy_type', 'is_active')
    list_filter = ('occupancy_type', 'is_active')
    search_fields = ('user__email', 'flat__flat_number')
