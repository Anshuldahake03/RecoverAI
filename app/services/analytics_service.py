import logging
from app.extensions import db
from app.models.transaction import Transaction
from app.models.recovery_prediction import RecoveryPrediction
from app.models.recovery_recommendation import RecoveryRecommendation
from app.models.recovery_action import RecoveryAction

logger = logging.getLogger(__name__)


def get_overview():
    total_transactions = Transaction.query.count()
    failed_transactions = Transaction.query.filter(
        Transaction.status.in_(['FAILED', 'PENDING'])
    ).count()
    revenue_at_risk = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter(Transaction.status.in_(['FAILED', 'PENDING'])).scalar() or 0

    recovered_transactions = Transaction.query.filter_by(status='RECOVERED').count()
    recovered_revenue = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter_by(status='RECOVERED').scalar() or 0

    eligible_for_recovery = RecoveryRecommendation.query.filter(
        RecoveryRecommendation.action.in_(['RETRY', 'SEND_PAYMENT_LINK', 'SEND_REMINDER'])
    ).count()

    recovery_attempts = RecoveryAction.query.filter(
        RecoveryAction.status.in_(['COMPLETED', 'FAILED'])
    ).count()

    recovery_rate = (recovered_transactions / eligible_for_recovery * 100) if eligible_for_recovery > 0 else 0

    return {
        'total_transactions': total_transactions,
        'failed_transactions': failed_transactions,
        'revenue_at_risk': round(revenue_at_risk, 2),
        'predicted_recoverable_revenue': round(revenue_at_risk * 0.6, 2),
        'recovery_attempts': recovery_attempts,
        'successful_recoveries': recovered_transactions,
        'recovered_revenue': round(recovered_revenue, 2),
        'recovery_rate': round(recovery_rate, 2)
    }


def get_recovery_trend():
    from sqlalchemy import func

    def monthly(model, statuses):
        rows = db.session.query(
            func.strftime('%Y-%m', Transaction.created_at).label('period'),
            func.count(Transaction.id),
            func.sum(Transaction.amount)
        ).filter(Transaction.status.in_(statuses)).group_by('period').all()
        return rows

    recovered = monthly(Transaction, ['RECOVERED'])
    at_risk = monthly(Transaction, ['FAILED', 'PENDING'])

    at_risk_map = {r[0]: (r[1], float(r[2]) if r[2] else 0.0) for r in at_risk}
    recovered_map = {r[0]: (r[1], float(r[2]) if r[2] else 0.0) for r in recovered}

    periods = sorted(set(recovered_map) | set(at_risk_map))
    return {
        'periods': periods,
        'recovered_revenue': [round(recovered_map.get(p, (0, 0.0))[1], 2) for p in periods],
        'recovered_count': [recovered_map.get(p, (0, 0.0))[0] for p in periods],
        'at_risk_revenue': [round(at_risk_map.get(p, (0, 0.0))[1], 2) for p in periods],
        'at_risk_count': [at_risk_map.get(p, (0, 0.0))[0] for p in periods]
    }


def get_recovery_analytics():
    action_dist = db.session.query(
        RecoveryRecommendation.action,
        db.func.count(RecoveryRecommendation.id)
    ).group_by(RecoveryRecommendation.action).all()

    action_success = db.session.query(
        RecoveryAction.action,
        RecoveryAction.status,
        db.func.count(RecoveryAction.id)
    ).group_by(RecoveryAction.action, RecoveryAction.status).all()

    failure_reasons = db.session.query(
        Transaction.failure_reason,
        db.func.count(Transaction.id)
    ).filter(Transaction.status.in_(['FAILED', 'PENDING'])) \
     .group_by(Transaction.failure_reason).all()

    action_outcomes_list = []
    for a, s, c in action_success:
        entry = next((e for e in action_outcomes_list if e['action'] == a), None)
        if entry is None:
            entry = {'action': a, 'status_counts': {}}
            action_outcomes_list.append(entry)
        entry['status_counts'][s] = c

    return {
        'action_distribution': {a: c for a, c in action_dist},
        'action_outcomes': action_outcomes_list,
        'failure_reason_distribution': {r: c for r, c in failure_reasons if r}
    }


def get_model_metrics():
    predictions = RecoveryPrediction.query.all()

    total = len(predictions)
    if total == 0:
        return {
            'total_predictions': 0,
            'avg_probability': 0,
            'model_version': None,
            'feature_version': None
        }

    avg_prob = sum(p.probability for p in predictions) / total
    model_version = predictions[0].model_version if predictions else None
    feature_version = predictions[0].feature_version if predictions else None

    high_conf = sum(1 for p in predictions if p.probability >= 0.7)
    med_conf = sum(1 for p in predictions if 0.4 <= p.probability < 0.7)
    low_conf = sum(1 for p in predictions if p.probability < 0.4)

    return {
        'total_predictions': total,
        'avg_probability': round(avg_prob, 4),
        'high_confidence_count': high_conf,
        'medium_confidence_count': med_conf,
        'low_confidence_count': low_conf,
        'model_version': model_version,
        'feature_version': feature_version
    }


def get_batch_recovery_report():
    overview = get_overview()
    recovery = get_recovery_analytics()
    model = get_model_metrics()

    policy_blocked = RecoveryAction.query.filter_by(status='REJECTED').count()
    escalated = RecoveryRecommendation.query.filter_by(action='ESCALATE').count()
    no_action = RecoveryRecommendation.query.filter_by(action='NO_ACTION').count()

    total_eligible = overview['recovery_attempts'] + policy_blocked
    success_rate = (
        overview['successful_recoveries'] / total_eligible * 100
    ) if total_eligible > 0 else 0

    return {
        'batch_size': overview['total_transactions'],
        'eligible_cases': overview['failed_transactions'],
        'cases_recommended_for_recovery': overview['predicted_recoverable_revenue'] > 0,
        'actions_attempted': overview['recovery_attempts'],
        'successful_recoveries': overview['successful_recoveries'],
        'recovered_revenue': overview['recovered_revenue'],
        'revenue_at_risk': overview['revenue_at_risk'],
        'revenue_recovery_rate': round(success_rate, 2),
        'policy_blocked_cases': policy_blocked,
        'escalated_cases': escalated,
        'no_action_cases': no_action,
        'action_distribution': recovery['action_distribution'],
        'model_summary': model
    }
