import logging
from datetime import datetime, timedelta
from app.extensions import db
from app.models.transaction import Transaction
from app.models.customer import Customer

logger = logging.getLogger(__name__)


class PredunningDetector:
    CARD_EXPIRY_WARNING_DAYS = 30
    MANDATE_EXPIRY_WARNING_DAYS = 14
    LOW_BALANCE_INDICATOR = 'insufficient_funds'
    HIGH_VALUE_THRESHOLD = 5000

    @staticmethod
    def detect_expiring_cards(days_ahead=30):
        cutoff = datetime.utcnow() + timedelta(days=days_ahead)
        failed_txns = Transaction.query.filter(
            Transaction.status.in_(['FAILED', 'PENDING']),
            Transaction.failure_reason == 'card_expired'
        ).all()

        alerts = []
        for txn in failed_txns:
            alerts.append({
                'transaction_id': txn.transaction_id,
                'customer_id': txn.customer_id,
                'amount': txn.amount,
                'alert_type': 'CARD_EXPIRING',
                'reason': 'Customer card has expired',
                'recommended_action': 'SEND_PAYMENT_LINK',
                'priority': 'HIGH' if txn.amount > PredunningDetector.HIGH_VALUE_THRESHOLD else 'MEDIUM'
            })

        return alerts

    @staticmethod
    def detect_repeated_failures(threshold=2):
        customers = Customer.query.filter(
            Customer.failed_count >= threshold
        ).all()

        alerts = []
        for customer in customers:
            recent_failures = Transaction.query.filter(
                Transaction.customer_id == customer.id,
                Transaction.status.in_(['FAILED', 'PENDING'])
            ).count()

            if recent_failures >= threshold:
                last_failure = Transaction.query.filter(
                    Transaction.customer_id == customer.id,
                    Transaction.status.in_(['FAILED', 'PENDING'])
                ).order_by(Transaction.created_at.desc()).first()

                if last_failure:
                    alerts.append({
                        'transaction_id': last_failure.transaction_id,
                        'customer_id': customer.id,
                        'amount': last_failure.amount,
                        'alert_type': 'REPEATED_FAILURE',
                        'reason': f'{recent_failures} consecutive failures',
                        'recommended_action': 'ESCALATE',
                        'priority': 'HIGH'
                    })

        return alerts

    @staticmethod
    def detect_high_value_at_risk():
        failed_high_value = Transaction.query.filter(
            Transaction.status.in_(['FAILED', 'PENDING']),
            Transaction.amount >= PredunningDetector.HIGH_VALUE_THRESHOLD
        ).all()

        alerts = []
        for txn in failed_high_value:
            alerts.append({
                'transaction_id': txn.transaction_id,
                'customer_id': txn.customer_id,
                'amount': txn.amount,
                'alert_type': 'HIGH_VALUE_AT_RISK',
                'reason': f'High-value transaction (₹{txn.amount}) at risk',
                'recommended_action': 'ESCALATE',
                'priority': 'CRITICAL'
            })

        return alerts

    @staticmethod
    def run_full_scan():
        all_alerts = []
        all_alerts.extend(PredunningDetector.detect_expiring_cards())
        all_alerts.extend(PredunningDetector.detect_repeated_failures())
        all_alerts.extend(PredunningDetector.detect_high_value_at_risk())

        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        all_alerts.sort(key=lambda x: priority_order.get(x['priority'], 4))

        logger.info(f"Pre-dunning scan: {len(all_alerts)} alerts detected")
        return {
            'alerts': all_alerts,
            'total': len(all_alerts),
            'critical': sum(1 for a in all_alerts if a['priority'] == 'CRITICAL'),
            'high': sum(1 for a in all_alerts if a['priority'] == 'HIGH'),
            'medium': sum(1 for a in all_alerts if a['priority'] == 'MEDIUM'),
            'scan_time': datetime.utcnow().isoformat()
        }
