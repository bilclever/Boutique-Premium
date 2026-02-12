# backend/apps/payments/serializers.py
from rest_framework import serializers
from .models import Payment
import re


class PaymentCreateSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(write_only=True)
    use_redirect = serializers.BooleanField(default=False)
    return_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = Payment
        fields = [
            'order_id', 'phone_number', 'network', 'amount',
            'description', 'use_redirect', 'return_url'
        ]
        extra_kwargs = {
            'amount': {'required': False},
            'description': {'required': False}
        }

    def validate_phone_number(self, value):
        """Valider le format du numéro de téléphone Togolais"""
        # Nettoyer le numéro
        clean_number = value.replace(' ', '').replace('-', '')

        # Formats acceptés: +228XXXXXXXX, 00228XXXXXXXX, 0XXXXXXXX
        pattern = r'^(\+228|00228|0)[0-9]{8}$'
        if not re.match(pattern, clean_number):
            raise serializers.ValidationError(
                "Format de numéro invalide. Exemples: +22890123456, 0022890123456, 090123456"
            )
        return clean_number

    def validate_network(self, value):
        """Valider le réseau"""
        if value not in ['FLOOZ', 'TMONEY']:
            raise serializers.ValidationError("Réseau doit être FLOOZ ou TMONEY")
        return value

    def validate(self, data):
        """Validation croisée"""
        if data.get('use_redirect') and not data.get('return_url'):
            raise serializers.ValidationError({
                'return_url': "Ce champ est requis lorsque use_redirect est True"
            })
        return data


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_email = serializers.CharField(source='order.user.email', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'identifier', 'tx_reference', 'order_number',
            'customer_email', 'customer_name', 'payment_method',
            'status', 'amount', 'currency', 'phone_number', 'network',
            'description', 'payment_reference', 'payment_method_detail',
            'payment_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'identifier', 'tx_reference', 'payment_reference',
            'payment_method_detail', 'payment_date', 'created_at', 'updated_at'
        ]

    def get_customer_name(self, obj):
        """Obtenir le nom complet du client"""
        user = obj.order.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.email


class PaymentStatusSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=False)
    tx_reference = serializers.CharField(required=False)

    def validate(self, data):
        if not data.get('identifier') and not data.get('tx_reference'):
            raise serializers.ValidationError({
                'identifier': 'Au moins un identifiant est requis (identifier ou tx_reference)'
            })
        return data