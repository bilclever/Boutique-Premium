# backend/apps/shipping/serializers.py
from rest_framework import serializers
from .models import ShippingZone, ShippingMethod

class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = ['id', 'name', 'method_type', 'price', 'min_days', 'max_days']

class ShippingZoneSerializer(serializers.ModelSerializer):
    methods = ShippingMethodSerializer(many=True, read_only=True)
    
    class Meta:
        model = ShippingZone
        fields = ['id', 'name', 'countries', 'methods']