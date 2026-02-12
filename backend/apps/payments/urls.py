# backend/apps/payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),

    # Route pour créer un paiement mobile (POST /api/payments/mobile-payment/initiate/)
    path('mobile-payment/initiate/',
         PaymentViewSet.as_view({'post': 'create'}),
         name='mobile-payment-initiate'),

    # Webhook pour les callbacks PayGate (POST /api/payments/webhook/)
    path('webhook/',
         PaymentViewSet.as_view({'post': 'webhook'}),
         name='payment-webhook'),

    # Vérifier le statut d'un paiement (POST /api/payments/check-status/)
    path('check-status/',
         PaymentViewSet.as_view({'post': 'check_status'}),
         name='payment-status'),

    # Consulter le solde (GET /api/payments/balance/)
    path('balance/',
         PaymentViewSet.as_view({'get': 'balance'}),
         name='payment-balance'),
]