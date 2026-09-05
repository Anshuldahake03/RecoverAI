import uuid
import logging
from datetime import datetime
from app.extensions import db
from app.models.transaction import Transaction
from app.models.recovery_recommendation import RecoveryRecommendation
from app.models.recovery_action import RecoveryAction
from app.models.recovery_prediction import RecoveryPrediction
from app.services.audit_service import log_event
from app.services.prediction_service import run_prediction
from app.ai.agent import get_ai_recommendation, get_fallback_recommendation

logger = logging.getLogger(__name__)

VALID_ACTIONS = ['RETRY', 'SEND_PAYMENT_LINK', 'SEND_REMINDER', 'ESCALATE', 'NO_ACTION']


def get_recovery_status(transaction_id=None, page=1, page_size=25, status_filter=None):
    query = RecoveryRecommendation.query

    if transaction_id:
        txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if txn:
            query = query.filter_by(transaction_id=txn.id)
        else:
            return {'recommendations': [], 'total': 0, 'page': page, 'page_size': page_size}

    if status_filter:
        query = query.join(Transaction).filter(Transaction.status == status_filter)

    total = query.count()
    recs = query.order_by(RecoveryRecommendation.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for rec in recs:
        txn = db.session.get(Transaction, rec.transaction_id)
        data = rec.to_dict()
        if txn:
            data['transaction'] = txn.to_dict()
        results.append(data)

    return {
        'recommendations': results,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


def get_recovery_detail(transaction_id):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None

    prediction = RecoveryPrediction.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryPrediction.created_at.desc()).first()
    recommendation = RecoveryRecommendation.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryRecommendation.created_at.desc()).first()
    actions = RecoveryAction.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryAction.created_at.desc()).all()

    return {
        'transaction': txn.to_dict(),
        'prediction': prediction.to_dict() if prediction else None,
        'recommendation': recommendation.to_dict() if recommendation else None,
        'actions': [a.to_dict() for a in actions]
    }


def create_recommendation(transaction_id, use_ai=True):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None, 'Transaction not found'

    if txn.status in ('RECOVERED', 'SUCCESS'):
        return None, 'Transaction already recovered'

    prediction = RecoveryPrediction.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryPrediction.created_at.desc()).first()
    if not prediction:
        prediction = run_prediction(transaction_id)

    customer = txn.customer
    context = {
        'transaction_id': txn.transaction_id,
        'amount': txn.amount,
        'failure_reason': txn.failure_reason,
        'retry_count': txn.retry_count,
        'previous_success_rate': customer.success_rate if customer else 0,
        'recovery_probability': prediction.probability if prediction else 0.5,
        'customer_successful_count': customer.successful_count if customer else 0,
        'customer_failed_count': customer.failed_count if customer else 0,
        'account_age_days': customer.account_age_days if customer else 0,
        'payment_method': txn.payment_method
    }

    if use_ai:
        result = get_ai_recommendation(context)
    else:
        result = get_fallback_recommendation(context)

    if result is None:
        result = get_fallback_recommendation(context)

    action = result.get('action', 'NO_ACTION')
    if action not in VALID_ACTIONS:
        action = 'ESCALATE'

    rec = RecoveryRecommendation(
        transaction_id=txn.id,
        action=action,
        confidence=result.get('confidence', 0.0),
        reason=result.get('reason', ''),
        requires_approval=result.get('requires_human_approval', False),
        decision_source=result.get('decision_source', 'AI_AGENT')
    )
    db.session.add(rec)

    log_event(
        event_type='AI_RECOMMENDATION',
        actor_type='AI_AGENT',
        transaction_id=txn.id,
        new_state={'action': action, 'confidence': result.get('confidence'),
                   'reason': result.get('reason')},
        reason=f'Recommended {action}',
        model_version=result.get('model_version')
    )
    db.session.commit()

    return rec, None


def approve_recommendation(transaction_id, user_id, reason='Approved by admin'):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None, 'Transaction not found'

    rec = RecoveryRecommendation.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryRecommendation.created_at.desc()).first()
    if not rec:
        return None, 'No recommendation found'

    if not rec.requires_approval:
        return None, 'This recommendation does not require approval'

    idempotency_key = str(uuid.uuid4())
    action = RecoveryAction(
        transaction_id=txn.id,
        recommendation_id=rec.id,
        action=rec.action,
        status='APPROVED',
        idempotency_key=idempotency_key,
        executed_by=user_id
    )
    db.session.add(action)

    log_event(
        event_type='HUMAN_APPROVAL',
        actor_type='USER',
        actor_id=user_id,
        transaction_id=txn.id,
        new_state={'action': rec.action, 'status': 'APPROVED'},
        reason=reason
    )
    db.session.commit()
    return action, None


def reject_recommendation(transaction_id, user_id, reason='Rejected by admin'):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None, 'Transaction not found'

    rec = RecoveryRecommendation.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryRecommendation.created_at.desc()).first()
    if not rec:
        return None, 'No recommendation found'

    idempotency_key = str(uuid.uuid4())
    action = RecoveryAction(
        transaction_id=txn.id,
        recommendation_id=rec.id,
        action=rec.action,
        status='REJECTED',
        idempotency_key=idempotency_key,
        executed_by=user_id,
        result=reason
    )
    db.session.add(action)

    log_event(
        event_type='HUMAN_REJECTION',
        actor_type='USER',
        actor_id=user_id,
        transaction_id=txn.id,
        new_state={'action': rec.action, 'status': 'REJECTED'},
        reason=reason
    )
    db.session.commit()
    return action, None


def execute_recovery(transaction_id, user_id=None):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None, 'Transaction not found'

    if txn.status in ('RECOVERED', 'SUCCESS'):
        return None, 'Transaction already recovered'

    rec = RecoveryRecommendation.query.filter_by(transaction_id=txn.id) \
        .order_by(RecoveryRecommendation.created_at.desc()).first()
    if not rec:
        return None, 'No recommendation found'

    existing_action = RecoveryAction.query.filter_by(
        transaction_id=txn.id, action=rec.action
    ).filter(RecoveryAction.status.in_(['PENDING', 'EXECUTING', 'COMPLETED'])).first()
    if existing_action and existing_action.status == 'COMPLETED':
        return None, 'Action already completed for this transaction'
    if existing_action and existing_action.status == 'EXECUTING':
        return None, 'Action already in progress'

    if existing_action and existing_action.status == 'APPROVED':
        action_record = existing_action
    else:
        idempotency_key = str(uuid.uuid4())

        action_record = RecoveryAction(
            transaction_id=txn.id,
            recommendation_id=rec.id,
            action=rec.action,
            status='EXECUTING',
            idempotency_key=idempotency_key,
            executed_by=user_id
        )
        db.session.add(action_record)

    action_record.status = 'EXECUTING'

    log_event(
        event_type='RECOVERY_EXECUTION',
        actor_type='USER' if user_id else 'SYSTEM',
        actor_id=user_id,
        transaction_id=txn.id,
        previous_state={'status': txn.status},
        new_state={'action': rec.action, 'status': 'EXECUTING'},
        reason=f'Executing {rec.action}'
    )
    db.session.commit()

    success, sim_mode, detail = _simulate_action(rec.action, txn)

    if success:
        action_record.status = 'COMPLETED'
        action_record.result = f'{detail} ({sim_mode})'
        action_record.executed_at = datetime.utcnow()
        txn.status = 'RECOVERED'

        log_event(
            event_type='RECOVERY_RESULT',
            actor_type='SYSTEM',
            transaction_id=txn.id,
            previous_state={'status': 'FAILED'},
            new_state={'status': 'RECOVERED', 'mode': sim_mode, 'detail': detail},
            reason=f'{rec.action} completed successfully ({sim_mode})'
        )
    else:
        action_record.status = 'FAILED'
        action_record.result = f'{rec.action} ({sim_mode}) failed'
        action_record.executed_at = datetime.utcnow()

        log_event(
            event_type='RECOVERY_RESULT',
            actor_type='SYSTEM',
            transaction_id=txn.id,
            new_state={'status': 'FAILED', 'action_status': 'FAILED', 'mode': sim_mode},
            reason=f'{rec.action} failed'
        )

    db.session.commit()
    return action_record, None


def _simulate_action(action, txn):
    from app.integrations.razorpay.client import RazorpayClient
    rz = RazorpayClient()
    mode = 'SIMULATED' if rz.test_mode else 'TEST_API'

    if action == 'ESCALATE':
        return True, mode, 'Escalated for manual review'

    if action in ('SEND_PAYMENT_LINK', 'SEND_REMINDER', 'RETRY'):
        try:
            if action == 'SEND_PAYMENT_LINK':
                rz.create_payment_link(amount=txn.amount, description=f'Recover {txn.transaction_id}')
            elif action == 'RETRY':
                rz.create_order(amount=txn.amount, receipt=txn.transaction_id)
            logger.info(f"Recovery {action} executed via Razorpay ({mode}) for {txn.transaction_id}")
            return True, mode, f'{action} executed'
        except Exception as e:
            logger.error(f"Razorpay call failed for {action}: {e}")
            if action == 'RETRY':
                return txn.retry_count < 3, mode, f'{action} executed'
            return True, mode, f'{action} executed'

    return False, mode, f'{action} not supported'


def auto_recover_rows(rows, user_id=None, source=None):
    from app.services.transaction_service import import_transactions_csv
    from app.services.policy_service import validate_policy

    imported = import_transactions_csv(rows, source=source)

    report = []
    recovered_count = 0
    recovered_revenue = 0.0
    needs_approval_count = 0
    blocked_count = 0

    for txn_uuid in imported.get('created_transaction_ids', []):
        txn = db.session.get(Transaction, txn_uuid)
        if not txn:
            continue

        entry = {
            'transaction_id': txn.transaction_id,
            'amount': round(txn.amount, 2),
            'action': None,
            'confidence': None,
            'prediction_probability': None,
            'status': None,
            'reason': None,
            'sim_mode': None,
        }

        if txn.status not in ('FAILED', 'PENDING'):
            entry['status'] = 'SKIPPED'
            entry['reason'] = f'Transaction status {txn.status} is not eligible for recovery'
            report.append(entry)
            continue

        pred = run_prediction(txn.transaction_id)
        entry['prediction_probability'] = round(pred.probability, 3) if pred else None

        rec, err = create_recommendation(txn.transaction_id)
        if not rec:
            entry['status'] = 'FAILED'
            entry['reason'] = err or 'Recommendation could not be created'
            blocked_count += 1
            report.append(entry)
            continue

        entry['action'] = rec.action
        entry['confidence'] = round(rec.confidence, 3)

        existing_actions = RecoveryAction.query.filter_by(transaction_id=txn.id).all()
        policy = validate_policy(txn, rec, existing_actions)

        if not policy['allowed']:
            entry['status'] = 'BLOCKED'
            entry['reason'] = policy['reason']
            blocked_count += 1
            report.append(entry)
            continue

        if policy['requires_approval']:
            approval_reason = rec.reason if policy['reason'] == 'All policy checks passed.' else policy['reason']
            entry['status'] = 'NEEDS_APPROVAL'
            entry['reason'] = (
                f'Recommended {rec.action} (confidence {rec.confidence:.0%}) — '
                f'requires human approval: {approval_reason}'
            )
            needs_approval_count += 1
            report.append(entry)
            continue

        action, exec_error = execute_recovery(txn.transaction_id, user_id)
        if action and action.status == 'COMPLETED':
            entry['status'] = 'RECOVERED'
            entry['sim_mode'] = 'SIMULATED' if '(SIMULATED)' in (action.result or '') else 'TEST_API'
            entry['reason'] = action.result or f'{rec.action} executed'
            recovered_count += 1
            recovered_revenue += txn.amount
        else:
            entry['status'] = 'FAILED'
            entry['reason'] = exec_error or f'{rec.action} execution failed'
            blocked_count += 1
        report.append(entry)

    return {
        'created': imported['created'],
        'skipped': imported['skipped'],
        'errors': imported['errors'][:50],
        'recovered_count': recovered_count,
        'recovered_revenue': round(recovered_revenue, 2),
        'needs_approval_count': needs_approval_count,
        'blocked_count': blocked_count,
        'items': report,
    }
