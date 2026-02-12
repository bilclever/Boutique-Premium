# backend/apps/shipping/views.py
from rest_framework import viewsets
from .models import ShippingZone
from .serializers import ShippingZoneSerializer


class ShippingZoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingZone.objects.filter(is_active=True).prefetch_related('methods')
    serializer_class = ShippingZoneSerializer


from django.shortcuts import render

# Create your views here.
