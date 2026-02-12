# backend/apps/payments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'identifier',
        'order_display',
        'phone_number',
        'network',
        'amount_display',
        'status_display',
        'payment_date',
        'created_at'
    ]

    list_filter = [
        'status',
        'network',
        'payment_method',
        'created_at',
        'payment_date'
    ]

    search_fields = [
        'identifier',
        'tx_reference',
        'payment_reference',
        'order__order_number',
        'order__user__email',
        'order__user__first_name',
        'order__user__last_name',
        'phone_number'
    ]

    readonly_fields = [
        'identifier',
        'tx_reference',
        'payment_reference',
        'created_at',
        'updated_at',
        'payment_date',
        'raw_request_preview',
        'raw_response_preview',
        'payment_link'
    ]

    fieldsets = (
        ('Informations de base', {
            'fields': (
                'order',
                'payment_link',
                'payment_method',
                'status',
                'amount',
                'currency'
            )
        }),
        ('Informations Mobile Money', {
            'fields': (
                'phone_number',
                'network',
                'description'
            )
        }),
        ('Identifiants PayGate', {
            'fields': (
                'identifier',
                'tx_reference',
                'payment_reference',
                'payment_method_detail'
            )
        }),
        ('Détails de la transaction', {
            'fields': (
                'payment_date',
                'error_message'
            )
        }),
        ('Données techniques', {
            'classes': ('collapse',),
            'fields': (
                'raw_request_preview',
                'raw_response_preview',
            )
        }),
        ('Dates', {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'updated_at'
            )
        }),
    )

    def order_display(self, obj):
        """Afficher le numéro de commande avec lien"""
        return format_html(
            '<a href="/admin/orders/order/{}/change/">{}</a>',
            obj.order.id,
            obj.order.order_number
        )

    order_display.short_description = 'Commande'
    order_display.admin_order_field = 'order__order_number'

    def amount_display(self, obj):
        """Afficher le montant formaté"""
        return f"{obj.amount} {obj.currency}"

    amount_display.short_description = 'Montant'
    amount_display.admin_order_field = 'amount'

    def status_display(self, obj):
        """Afficher le statut avec badge coloré"""
        status_colors = {
            'pending': 'orange',
            'initiated': 'blue',
            'processing': 'purple',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = 'Statut'
    status_display.admin_order_field = 'status'

    def raw_request_preview(self, obj):
        """Aperçu formaté de la requête brute"""
        if obj.raw_request:
            import json
            try:
                formatted_json = json.dumps(obj.raw_request, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto;">{}</pre>',
                    formatted_json)
            except:
                return str(obj.raw_request)
        return "-"

    raw_request_preview.short_description = "Requête PayGate (aperçu)"

    def raw_response_preview(self, obj):
        """Aperçu formaté de la réponse brute"""
        if obj.raw_response:
            import json
            try:
                formatted_json = json.dumps(obj.raw_response, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto;">{}</pre>',
                    formatted_json)
            except:
                return str(obj.raw_response)
        return "-"

    raw_response_preview.short_description = "Réponse PayGate (aperçu)"

    def payment_link(self, obj):
        """Lien vers la page de paiement PayGate (si initié)"""
        if obj.status == 'initiated' and obj.identifier:
            from django.conf import settings
            paygate_url = f"https://paygateglobal.com/v1/page?token={settings.PAYGATE_API_KEY}&amount={int(obj.amount)}&identifier={obj.identifier}"
            return format_html(
                '<a href="{}" target="_blank" style="background: #007cba; color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none;">📱 Page de paiement</a>',
                paygate_url
            )
        return "-"

    payment_link.short_description = "Lien PayGate"

    def has_add_permission(self, request):
        """Empêcher l'ajout manuel de paiements depuis l'admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression de paiements depuis l'admin"""
        return False

    def get_queryset(self, request):
        """Optimiser les requêtes pour l'admin"""
        return super().get_queryset(request).select_related(
            'order',
            'order__user'
        ).prefetch_related(
            'order__items'
        )

    # Actions personnalisées
    actions = ['check_payment_status', 'mark_as_completed', 'mark_as_failed']

    def check_payment_status(self, request, queryset):
        """Action pour vérifier le statut des paiements sélectionnés"""
        from .services import PayGateGlobalService
        paygate_service = PayGateGlobalService()

        updated_count = 0
        for payment in queryset:
            if payment.identifier or payment.tx_reference:
                status_data = paygate_service.check_payment_status(
                    payment.identifier,
                    payment.tx_reference
                )

                if 'error' not in status_data:
                    paygate_status = status_data.get('status')
                    if paygate_status == 0 and payment.status != 'completed':
                        payment.status = 'completed'
                        payment.payment_reference = status_data.get('payment_reference', '')
                        payment.payment_method_detail = status_data.get('payment_method', '')
                        payment.save()
                        updated_count += 1

        self.message_user(
            request,
            f"Statut vérifié pour {updated_count} paiement(s)."
        )

    check_payment_status.short_description = "✅ Vérifier le statut PayGate"

    def mark_as_completed(self, request, queryset):
        """Marquer les paiements comme complétés (manuellement)"""
        updated_count = queryset.update(status='completed')
        self.message_user(
            request,
            f"{updated_count} paiement(s) marqué(s) comme complété(s)."
        )

    mark_as_completed.short_description = "✅ Marquer comme complété"

    def mark_as_failed(self, request, queryset):
        """Marquer les paiements comme échoués (manuellement)"""
        updated_count = queryset.update(status='failed')
        self.message_user(
            request,
            f"{updated_count} paiement(s) marqué(s) comme échoué(s)."
        )

    mark_as_failed.short_description = "❌ Marquer comme échoué"

    # Configuration de l'interface
    list_per_page = 20
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    # Personnalisation des filtres
    list_filter = [
        ('status', admin.AllValuesFieldListFilter),
        ('network', admin.AllValuesFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        ('payment_date', admin.DateFieldListFilter),
    ]

    # Export des données
    def get_export_fields(self):
        """Champs pour l'export"""
        return [
            'identifier', 'order__order_number', 'phone_number', 'network',
            'amount', 'currency', 'status', 'payment_date', 'created_at'
        ]