# backend/apps/payments/views.py
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.orders.models import Order
from .models import Payment
from .serializers import PaymentCreateSerializer, PaymentSerializer, PaymentStatusSerializer
from .services import PayGateGlobalService

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Payment.objects.all().select_related('order', 'order__user')

    def get_queryset(self):
        return self.queryset.filter(order__user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def create(self, request):
        """
        POST /api/payments/mobile-payment/initiate/
        Créer un nouveau paiement mobile money
        """
        serializer = PaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_id = serializer.validated_data['order_id']

            # Récupérer et valider la commande
            try:
                order = Order.objects.get(id=order_id, user=request.user)
            except Order.DoesNotExist:
                return Response(
                    {'error': 'Commande non trouvée'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Vérifier si la commande peut être payée
            if order.payment_status == 'paid':
                return Response(
                    {'error': 'Cette commande a déjà été payée'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Vérifier si un paiement existe déjà pour cette commande
            existing_payment = Payment.objects.filter(order=order).first()
            if existing_payment:
                if existing_payment.status == 'completed':
                    return Response(
                        {'error': 'Un paiement réussi existe déjà pour cette commande'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif existing_payment.status == 'initiated':
                    return Response(
                        {'error': 'Un paiement est déjà en cours pour cette commande'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Créer le paiement
            payment = Payment.objects.create(
                order=order,
                phone_number=serializer.validated_data['phone_number'],
                network=serializer.validated_data['network'],
                amount=order.total,  # Montant de la commande
                description=serializer.validated_data.get('description', ''),
                currency='XOF'
            )

            paygate_service = PayGateGlobalService()

            if serializer.validated_data.get('use_redirect', False):
                # Méthode 2: Redirection vers page PayGate
                return_url = serializer.validated_data.get('return_url', '')
                payment_url = paygate_service.generate_redirect_url(payment, return_url)

                return Response({
                    'success': True,
                    'payment_id': payment.id,
                    'identifier': payment.identifier,
                    'payment_url': payment_url,
                    'method': 'redirect',
                    'message': 'Redirigez vers la page de paiement'
                })
            else:
                # Méthode 1: API directe
                result = paygate_service.initiate_direct_payment(payment)

                if result['success']:
                    return Response({
                        'success': True,
                        'payment_id': payment.id,
                        'identifier': payment.identifier,
                        'tx_reference': result['tx_reference'],
                        'method': 'direct',
                        'message': result['message']
                    })
                else:
                    return Response({
                        'success': False,
                        'error': result['error'],
                        'status_code': result.get('status_code')
                    }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Erreur création paiement: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la création du paiement'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        GET /api/payments/{id}/status/
        Récupérer le statut d'un paiement spécifique
        """
        payment = self.get_object()

        paygate_service = PayGateGlobalService()
        status_data = paygate_service.check_payment_status(
            identifier=payment.identifier,
            tx_reference=payment.tx_reference
        )

        if 'error' in status_data:
            return Response(
                {'error': status_data['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mettre à jour le statut local si nécessaire
        paygate_status = status_data.get('status')
        if paygate_status == 0 and payment.status != 'completed':  # Paiement réussi
            payment.status = 'completed'
            payment.payment_reference = status_data.get('payment_reference', '')
            payment.payment_date = status_data.get('datetime')
            payment.payment_method_detail = status_data.get('payment_method', '')
            payment.save()

            # Mettre à jour la commande
            order = payment.order
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()

        return Response({
            'local_status': payment.status,
            'paygate_status': status_data
        })

    @action(detail=False, methods=['post'])
    @method_decorator(csrf_exempt)
    def webhook(self, request):
        """
        POST /api/payments/webhook/
        Webhook pour les notifications PayGate Global
        Cette endpoint ne requiert pas d'authentification
        """
        try:
            webhook_data = request.data
            logger.info(f"Webhook PayGate reçu: {webhook_data}")

            paygate_service = PayGateGlobalService()
            result = paygate_service.process_webhook(webhook_data)

            if result['success']:
                return Response({'status': 'success'})
            else:
                logger.error(f"Erreur traitement webhook: {result['error']}")
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Erreur traitement webhook: {str(e)}")
            return Response(
                {'error': 'Erreur lors du traitement du webhook'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def check_status(self, request):
        """
        POST /api/payments/check-status/
        Vérifier le statut d'un paiement par identifiant
        """
        serializer = PaymentStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        identifier = serializer.validated_data.get('identifier')
        tx_reference = serializer.validated_data.get('tx_reference')

        # Vérifier que l'utilisateur a accès à ce paiement
        if identifier:
            try:
                payment = Payment.objects.get(
                    identifier=identifier,
                    order__user=request.user
                )
            except Payment.DoesNotExist:
                return Response(
                    {'error': 'Paiement non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

        paygate_service = PayGateGlobalService()
        status_data = paygate_service.check_payment_status(identifier, tx_reference)

        if 'error' in status_data:
            return Response(
                {'error': status_data['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status_data)

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """
        GET /api/payments/balance/
        Consulter le solde des comptes (nécessite IP whitelistée)
        """
        paygate_service = PayGateGlobalService()
        balance_data = paygate_service.get_balance()

        if 'error' in balance_data:
            return Response(
                {'error': balance_data['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(balance_data)

    def list(self, request):
        """
        GET /api/payments/
        Lister les paiements de l'utilisateur
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        GET /api/payments/{id}/
        Récupérer un paiement spécifique
        """
        payment = self.get_object()
        serializer = self.get_serializer(payment)
        return Response(serializer.data)