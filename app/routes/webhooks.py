import logging
import hashlib
import hmac
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.services.audit_service import log_event
from app.services.ledger_service import HashChainedLedger

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint('webhooks', __name__)


@webhooks_bp.route('/razorpay', methods=['POST'])
def razorpay_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Razorpay-Signature', '')
    event_id = request.headers.get('x-razorpay-event-id', '')

    import os
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    if webhook_secret:
        expected = hmac.new(
            webhook_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.warning(f"Invalid webhook signature for event {event_id}")
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

    event = data.get('event', '')
    payload_data = data.get('payload', {})

    logger.info(f"Webhook received: {event} id={event_id}")

    try:
        if event == 'payment.failed':
            _handle_payment_failed(payload_data, event_id)
        elif event == 'payment.captured':
            _handle_payment_captured(payload_data, event_id)
        elif event == 'subscription.pending':
            _handle_subscription_pending(payload_data, event_id)
        elif event == 'subscription.halted':
            _handle_subscription_halted(payload_data, event_id)
        elif event == 'subscription.charged':
            _handle_subscription_charged(payload_data, event_id)
        elif event == 'order.paid':
            _handle_order_paid(payload_data, event_id)
        else:
            logger.info(f"Unhandled webhook event: {event}")

        HashChainedLedger.append_entry(
            event_type='WEBHOOK_RECEIVED',
            payload={'event': event, 'event_id': event_id, 'processed': True},
            actor_type='RAZORPAY',
            correlation_id=event_id
        )

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        HashChainedLedger.append_entry(
            event_type='WEBHOOK_ERROR',
            payload={'event': event, 'error': str(e)},
            actor_type='RAZORPAY',
            correlation_id=event_id
        )
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'ok'})


def _handle_payment_failed(payload, event_id):
    payment = payload.get('payment', {})
    entity = payment.get('entity', {})

    amount = entity.get('amount', 0) / 100
    method = entity.get('method', 'unknown')
    error_code = entity.get('error_code', '')
    error_description = entity.get('error_description', '')
    order_id = entity.get('order_id', '')

    failure_reason = _map_error_to_reason(error_code)

    customer_id = entity.get('customer_id', '')
    customer = None
    if customer_id:
        customer = Customer.query.filter_by(external_customer_id=customer_id).first()
        if not customer:
            customer = Customer(
                external_customer_id=customer_id,
                successful_count=0,
                failed_count=1,
                success_rate=0.0,
                account_age_days=0
            )
            db.session.add(customer)
            db.session.flush()
    else:
        customer = Customer(
            external_customer_id=f'WEBHOOK-{customer_id or event_id}',
            successful_count=0,
            failed_count=1,
            success_rate=0.0,
            account_age_days=0
        )
        db.session.add(customer)
        db.session.flush()

    txn_id = entity.get('id', f'RZP-{event_id}')
    existing = Transaction.query.filter_by(transaction_id=txn_id).first()
    if existing:
        existing.status = 'FAILED'
        existing.failure_reason = failure_reason
        existing.updated_at = datetime.utcnow()
    else:
        txn = Transaction(
            transaction_id=txn_id,
            customer_id=customer.id,
            amount=amount,
            currency=entity.get('currency', 'INR'),
            payment_method=method,
            status='FAILED',
            failure_reason=failure_reason,
            retry_count=0
        )
        db.session.add(txn)

    customer.failed_count += 1
    total = customer.successful_count + customer.failed_count
    customer.success_rate = customer.successful_count / total if total > 0 else 0

    db.session.commit()

    log_event(
        event_type='WEBHOOK_PAYMENT_FAILED',
        actor_type='RAZORPAY',
        transaction_id=txn_id,
        new_state={'error_code': error_code, 'failure_reason': failure_reason},
        reason=f'Payment failed: {error_description}',
        correlation_id=event_id
    )


def _handle_payment_captured(payload, event_id):
    payment = payload.get('payment', {})
    entity = payment.get('entity', {})

    txn_id = entity.get('id', '')
    if txn_id:
        txn = Transaction.query.filter_by(transaction_id=txn_id).first()
        if txn:
            txn.status = 'RECOVERED'
            txn.updated_at = datetime.utcnow()
            db.session.commit()

            log_event(
                event_type='WEBHOOK_PAYMENT_CAPTURED',
                actor_type='RAZORPAY',
                transaction_id=txn_id,
                previous_state={'status': 'FAILED'},
                new_state={'status': 'RECOVERED'},
                reason='Payment captured successfully',
                correlation_id=event_id
            )


def _handle_subscription_pending(payload, event_id):
    subscription = payload.get('subscription', {})
    entity = subscription.get('entity', {})

    sub_id = entity.get('id', '')
    customer_id = entity.get('customer_id', '')

    logger.info(f"Subscription pending: {sub_id} customer={customer_id}")

    log_event(
        event_type='WEBHOOK_SUBSCRIPTION_PENDING',
        actor_type='RAZORPAY',
        new_state={'subscription_id': sub_id, 'customer_id': customer_id},
        reason='Subscription payment failed, entering pending state',
        correlation_id=event_id
    )


def _handle_subscription_halted(payload, event_id):
    subscription = payload.get('subscription', {})
    entity = subscription.get('entity', {})

    sub_id = entity.get('id', '')
    logger.warning(f"Subscription HALTED: {sub_id} — all retries exhausted")

    log_event(
        event_type='WEBHOOK_SUBSCRIPTION_HALTED',
        actor_type='RAZORPAY',
        new_state={'subscription_id': sub_id},
        reason='All retry attempts exhausted, subscription halted',
        correlation_id=event_id
    )


def _handle_subscription_charged(payload, event_id):
    subscription = payload.get('subscription', {})
    entity = subscription.get('entity', {})

    sub_id = entity.get('id', '')
    logger.info(f"Subscription charged successfully: {sub_id}")

    log_event(
        event_type='WEBHOOK_SUBSCRIPTION_CHARGED',
        actor_type='RAZORPAY',
        new_state={'subscription_id': sub_id},
        reason='Subscription charged successfully',
        correlation_id=event_id
    )


def _handle_order_paid(payload, event_id):
    order = payload.get('order', {})
    entity = order.get('entity', {})

    order_id = entity.get('id', '')
    amount = entity.get('amount', 0) / 100

    logger.info(f"Order paid: {order_id} amount=₹{amount}")

    log_event(
        event_type='WEBHOOK_ORDER_PAID',
        actor_type='RAZORPAY',
        new_state={'order_id': order_id, 'amount': amount},
        reason='Order paid successfully',
        correlation_id=event_id
    )


def _map_error_to_reason(error_code):
    mapping = {
        'bad_vpa': 'authentication_failed',
        'invalid_vpa': 'authentication_failed',
        'insufficient_funds': 'insufficient_funds',
        'card_expired': 'card_expired',
        'invalid_card': 'authentication_failed',
        'payment_disabled': 'technical_error',
        'browser_blocked': 'technical_error',
        'do_not_honor': 'bank_declined',
        'issuer_unavailable': 'technical_error',
        'lost_card': 'bank_declined',
        'stolen_card': 'bank_declined',
        'expired_card': 'card_expired',
        'incorrect_pin': 'authentication_failed',
        'maximum_attempts_reached': 'authentication_failed',
        'upi_payer_declined': 'bank_declined',
        'mandate_inactive': 'mandate_revoked',
        'mandate_expired': 'mandate_expired',
    }
    return mapping.get(error_code, 'temporary_failure')
