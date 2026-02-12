# backend/apps/shipping/models.py
from django.db import models
from django.core.validators import MinValueValidator

class ShippingZone(models.Model):
    name = models.CharField(max_length=100)
    countries = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class ShippingMethod(models.Model):
    METHOD_TYPES = [
        ('standard', 'Livraison Standard'),
        ('express', 'Livraison Express'),
        ('priority', 'Livraison Prioritaire'),
    ]
    
    name = models.CharField(max_length=100)
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name='methods')
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES, default='standard')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    min_days = models.IntegerField(default=3)
    max_days = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.zone.name}"