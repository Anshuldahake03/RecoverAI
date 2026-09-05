import logging
from app.extensions import db
from app.models.transaction import Transaction
from app.models.recovery_prediction import RecoveryPrediction
from app.ml.predict import predict_recovery_probability, MODEL_VERSION, FEATURE_VERSION

logger = logging.getLogger(__name__)


def get_prediction(transaction_id):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None
    prediction = RecoveryPrediction.query.filter_by(
        transaction_id=txn.id
    ).order_by(RecoveryPrediction.created_at.desc()).first()
    return prediction


def run_prediction(transaction_id):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return None

    customer = txn.customer
    features = {
        'amount': txn.amount,
        'payment_method': txn.payment_method,
        'failure_reason': txn.failure_reason,
        'retry_count': txn.retry_count,
        'customer_successful_count': customer.successful_count if customer else 0,
        'customer_failed_count': customer.failed_count if customer else 0,
        'historical_success_rate': customer.success_rate if customer else 0,
        'account_age_days': customer.account_age_days if customer else 0,
    }

    probability = predict_recovery_probability(features)

    prediction = RecoveryPrediction(
        transaction_id=txn.id,
        probability=probability,
        model_version=MODEL_VERSION,
        feature_version=FEATURE_VERSION
    )
    db.session.add(prediction)
    db.session.commit()

    logger.info(f"Prediction for {transaction_id}: {probability:.4f}")
    return prediction
