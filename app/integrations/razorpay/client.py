import os
import logging
import requests

logger = logging.getLogger(__name__)


class RazorpayClient:
    def __init__(self):
        self.key_id = os.environ.get('RAZORPAY_KEY_ID', '')
        self.key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
        self.base_url = 'https://api.razorpay.com/v1'
        self.test_mode = not bool(self.key_secret)

    def _headers(self):
        import base64
        credentials = base64.b64encode(
            f'{self.key_id}:{self.key_secret}'.encode()
        ).decode()
        return {'Authorization': f'Basic {credentials}', 'Content-Type': 'application/json'}

    def create_order(self, amount, currency='INR', receipt=None, notes=None):
        if self.test_mode:
            logger.info("Razorpay test mode - simulating order creation")
            return {
                'id': f'order_test_{receipt or "simulated"}',
                'amount': amount,
                'currency': currency,
                'status': 'created'
            }

        try:
            payload = {
                'amount': int(amount * 100),
                'currency': currency,
                'receipt': receipt,
                'notes': notes or {}
            }
            response = requests.post(
                f'{self.base_url}/orders', json=payload,
                headers=self._headers(), timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}")
            return None

    def verify_payment(self, payment_id, order_id):
        if self.test_mode:
            logger.info("Razorpay test mode - simulating payment verification")
            return {'status': 'captured', 'id': payment_id, 'order_id': order_id}

        try:
            response = requests.get(
                f'{self.base_url}/payments/{payment_id}',
                headers=self._headers(), timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Razorpay payment verification failed: {e}")
            return None

    def create_payment_link(self, amount, description=None, customer=None):
        if self.test_mode:
            logger.info("Razorpay test mode - simulating payment link creation")
            return {
                'id': f'plink_test_simulated',
                'short_url': 'https://rzp.io/test/simulated',
                'status': 'created'
            }

        try:
            payload = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'description': description or 'Payment recovery',
                'customer': customer or {}
            }
            response = requests.post(
                f'{self.base_url}/payment_links', json=payload,
                headers=self._headers(), timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Razorpay payment link creation failed: {e}")
            return None

    def verify_webhook_signature(self, payload, signature):
        if self.test_mode:
            return True

        import hmac as _hmac
        import hashlib
        expected = _hmac.new(
            self.key_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return _hmac.compare_digest(expected, signature)


razorpay_client = RazorpayClient()
