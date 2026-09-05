import os
import logging

logger = logging.getLogger(__name__)

POLICY_CONFIG = {
    'MAX_AUTOMATIC_RETRY_COUNT': int(os.environ.get('MAX_AUTOMATIC_RETRY_COUNT', 1)),
    'MAX_AUTOMATIC_ACTION_AMOUNT': int(os.environ.get('MAX_AUTOMATIC_ACTION_AMOUNT', 10000)),
    'REQUIRE_HUMAN_APPROVAL_ABOVE_LIMIT': True,
    'RECOVERY_WINDOW_DAYS': 30,
    'ALLOWED_ACTIONS': ['RETRY', 'SEND_PAYMENT_LINK', 'SEND_REMINDER', 'ESCALATE', 'NO_ACTION'],
    'AUTO_ELIGIBLE_ACTIONS': ['RETRY', 'SEND_REMINDER'],
}


def validate_policy(transaction, recommendation, existing_actions=None):
    result = {
        'allowed': True,
        'requires_approval': False,
        'reason': 'All policy checks passed.',
        'checks': {}
    }

    if transaction.status in ('RECOVERED', 'SUCCESS'):
        result['allowed'] = False
        result['reason'] = 'Transaction already recovered/successful'
        result['checks']['transaction_state'] = 'BLOCKED'
        return result
    result['checks']['transaction_state'] = 'PASS'

    if recommendation is None:
        result['allowed'] = False
        result['reason'] = 'No recommendation exists for this transaction'
        result['checks']['recommendation'] = 'BLOCKED'
        return result

    if recommendation.action == 'RETRY' and transaction.retry_count >= POLICY_CONFIG['MAX_AUTOMATIC_RETRY_COUNT']:
        result['allowed'] = False
        result['reason'] = f'Maximum retry count ({POLICY_CONFIG["MAX_AUTOMATIC_RETRY_COUNT"]}) reached'
        result['checks']['retry_limit'] = 'BLOCKED'
        return result
    result['checks']['retry_limit'] = 'PASS'

    if recommendation.action not in POLICY_CONFIG['ALLOWED_ACTIONS']:
        result['allowed'] = False
        result['reason'] = f'Action {recommendation.action} not in allowed actions'
        result['checks']['action_validity'] = 'BLOCKED'
        return result
    result['checks']['action_validity'] = 'PASS'

    if transaction.amount > POLICY_CONFIG['MAX_AUTOMATIC_ACTION_AMOUNT']:
        result['requires_approval'] = True
        result['reason'] = f'Amount ₹{transaction.amount} exceeds automatic limit ₹{POLICY_CONFIG["MAX_AUTOMATIC_ACTION_AMOUNT"]}'
        result['checks']['amount_limit'] = 'APPROVAL_REQUIRED'
    else:
        result['checks']['amount_limit'] = 'PASS'

    if existing_actions:
        active = [a for a in existing_actions if a.status in ('PENDING', 'EXECUTING', 'APPROVED')]
        if active:
            result['allowed'] = False
            result['reason'] = 'Active action already exists for this transaction'
            result['checks']['duplicate_action'] = 'BLOCKED'
            return result
    result['checks']['duplicate_action'] = 'PASS'

    if recommendation.action in ('ESCALATE', 'NO_ACTION'):
        result['requires_approval'] = True
        result['checks']['escalation'] = 'APPROVAL_REQUIRED'

    if recommendation.confidence < 0.3:
        result['requires_approval'] = True
        result['checks']['low_confidence'] = 'APPROVAL_REQUIRED'

    if recommendation.requires_approval:
        result['requires_approval'] = True

    return result


def get_policy_config():
    return POLICY_CONFIG.copy()
