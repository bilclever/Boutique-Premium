# backend/apps/shipping/admin.py
from django.contrib import admin
from .models import ShippingZone, ShippingMethod

class ShippingMethodInline(admin.TabularInline):
    model = ShippingMethod
    extra = 1

@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    inlines = [ShippingMethodInline]

@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'zone', 'method_type', 'price', 'is_active']
    list_filter = ['method_type', 'is_active', 'zone']