# backend/apps/payments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from apps.orders.models import Order


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('initiated', 'Initiated'),
        ('processing', 'En traitement'),
        ('completed', 'Complétée'),
        ('failed', 'Échouée'),
        ('refunded', 'Remboursée'),
        ('cancelled', 'Annulée'),
    ]

    NETWORK_CHOICES = [
        ('FLOOZ', 'FLOOZ'),
        ('TMONEY', 'T-Money'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('paygate', 'PayGate'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mobile_money')

    # Identifiants PayGate Global
    tx_reference = models.CharField(max_length=100, blank=True)  # Référence PayGate
    identifier = models.CharField(max_length=100, blank=True)  # Notre référence unique
    payment_reference = models.CharField(max_length=100, blank=True)  # Référence Flooz/T-Money

    # Informations de paiement mobile
    phone_number = models.CharField(max_length=20, blank=True)
    network = models.CharField(max_length=10, choices=NETWORK_CHOICES, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='XOF')  # FCFA

    # Métadonnées de transaction
    description = models.TextField(blank=True)
    payment_method_detail = models.CharField(max_length=100, blank=True)

    # Données de réponse
    error_message = models.TextField(blank=True)
    raw_request = models.JSONField(blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)

    # Timestamps
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.identifier} for {self.order.order_number}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'