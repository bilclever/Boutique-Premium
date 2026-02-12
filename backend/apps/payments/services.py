# backend/apps/payments/services.py
import requests
import json
import logging
from django.conf import settings
from django.utils import timezone

from .models import Payment

logger = logging.getLogger(__name__)


class PayGateGlobalService:
    """
    Service pour l'intégration avec PayGate Global (FLOOZ/T-Money)
    """

    def __init__(self):
        self.api_key = settings.PAYGATE_API_KEY
        self.api_url = settings.PAYGATE_API_URL
        self.page_url = settings.PAYGATE_PAGE_URL
        self.status_url = settings.PAYGATE_STATUS_URL

    def initiate_direct_payment(self, payment):
        """
        Méthode 1: Paiement direct via API
        """
        data = {
            'auth_token': self.api_key,
            'phone_number': payment.phone_number,
            'amount': str(int(payment.amount)),
            'description': payment.description or f"Paiement commande {payment.order.order_number}",
            'identifier': payment.identifier,
            'network': payment.network
        }

        try:
            logger.info(f"Envoi requête PayGate: {data}")

            response = requests.post(
                self.api_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            response_data = response.json()
            logger.info(f"Réponse PayGate: {response_data}")

            payment.raw_request = data
            payment.raw_response = response_data

            if response.status_code == 200:
                status_code = response_data.get('status')

                if status_code == 0:
                    payment.tx_reference = response_data.get('tx_reference')
                    payment.status = 'initiated'
                    payment.save()

                    return {
                        'success': True,
                        'tx_reference': response_data.get('tx_reference'),
                        'status': status_code,
                        'message': 'Paiement initié avec succès'
                    }
                else:
                    error_messages = {
                        2: 'Jeton d\'authentification invalide',
                        4: 'Paramètres invalides',
                        6: 'Doublon détecté'
                    }
                    error_message = error_messages.get(status_code, f'Erreur: {status_code}')
                    payment.status = 'failed'
                    payment.error_message = error_message
                    payment.save()

                    return {
                        'success': False,
                        'error': error_message,
                        'status_code': status_code
                    }
            else:
                error_msg = f'Erreur HTTP: {response.status_code}'
                payment.status = 'failed'
                payment.error_message = error_msg
                payment.save()

                return {
                    'success': False,
                    'error': error_msg
                }

        except requests.RequestException as e:
            logger.error(f"Erreur connexion PayGate: {str(e)}")
            error_msg = 'Erreur de connexion au service de paiement'
            payment.status = 'failed'
            payment.error_message = error_msg
            payment.save()

            return {
                'success': False,
                'error': error_msg
            }

    def generate_redirect_url(self, payment, return_url=None):
        """
        Méthode 2: Générer l'URL de redirection
        """
        params = {
            'token': self.api_key,
            'amount': str(int(payment.amount)),
            'description': payment.description or f"Paiement commande {payment.order.order_number}",
            'identifier': payment.identifier
        }

        if return_url:
            params['url'] = return_url
        if payment.phone_number:
            params['phone'] = payment.phone_number
        if payment.network:
            params['network'] = payment.network

        query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        payment_url = f"{self.page_url}?{query_string}"

        payment.raw_request = params
        payment.status = 'initiated'
        payment.save()

        return payment_url

    def check_payment_status(self, identifier=None, tx_reference=None):
        """
        Vérifier le statut d'un paiement
        """
        if not identifier and not tx_reference:
            return {'error': 'Identifier ou tx_reference requis'}

        if tx_reference:
            data = {'auth_token': self.api_key, 'tx_reference': tx_reference}
            url = self.status_url
        else:
            data = {'auth_token': self.api_key, 'identifier': identifier}
            url = 'https://paygateglobal.com/api/v2/status'

        try:
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Erreur HTTP: {response.status_code}'}

        except requests.RequestException as e:
            logger.error(f"Erreur vérification statut: {str(e)}")
            return {'error': 'Erreur de connexion au service'}

    def process_webhook(self, webhook_data):
        """
        Traiter les webhooks de confirmation
        """
        required_fields = ['tx_reference', 'identifier', 'amount', 'payment_method', 'phone_number']

        for field in required_fields:
            if field not in webhook_data:
                logger.error(f"Champ manquant: {field}")
                return {'success': False, 'error': f'Champ manquant: {field}'}

        try:
            payment = Payment.objects.get(identifier=webhook_data['identifier'])

            if payment.status == 'completed':
                return {'success': True, 'message': 'Paiement déjà complété'}

            payment.tx_reference = webhook_data['tx_reference']
            payment.payment_reference = webhook_data.get('payment_reference', '')
            payment.payment_method_detail = webhook_data['payment_method']
            payment.phone_number = webhook_data['phone_number']
            payment.raw_response = webhook_data
            payment.status = 'completed'
            payment.payment_date = timezone.now()
            payment.save()

            order = payment.order
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()

            logger.info(f"Paiement {payment.identifier} complété via webhook")
            return {'success': True, 'payment_id': payment.id}

        except Payment.DoesNotExist:
            logger.error(f"Paiement non trouvé: {webhook_data['identifier']}")
            return {'success': False, 'error': 'Paiement non trouvé'}
        except Exception as e:
            logger.error(f"Erreur traitement webhook: {str(e)}")
            return {'success': False, 'error': 'Erreur lors du traitement'}

    def get_balance(self):
        """
        Consulter le solde
        """
        data = {'auth_token': self.api_key}

        try:
            response = requests.post(
                'https://paygateglobal.com/api/v1/check-balance',
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Erreur HTTP: {response.status_code}'}

        except requests.RequestException as e:
            logger.error(f"Erreur consultation solde: {str(e)}")
            return {'error': 'Erreur de connexion'}