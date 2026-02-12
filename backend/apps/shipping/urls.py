# backend/apps/shipping/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShippingZoneViewSet

router = DefaultRouter()
router.register(r'zones', ShippingZoneViewSet)

urlpatterns = [
    path('', include(router.urls)),
]