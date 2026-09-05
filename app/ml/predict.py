import os
import pickle
import numpy as np
import logging

logger = logging.getLogger(__name__)

MODEL_VERSION = 'v1.0'
FEATURE_VERSION = 'v1.0'
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'generated', 'model.pkl')

_model = None


def load_model():
    global _model
    if _model is not None:
        return _model

    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                _model = pickle.load(f)
            logger.info("ML model loaded successfully")
            return _model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    logger.warning("No trained model found, using rule-based predictor")
    return None


def predict_recovery_probability(features):
    model = load_model()

    if model is not None:
        try:
            feature_vector = _prepare_features(features)
            proba = model.predict_proba(feature_vector.reshape(1, -1))[0][1]
            return round(float(proba), 4)
        except Exception as e:
            logger.error(f"Model prediction failed: {e}, falling back to rules")

    return _rule_based_predict(features)


def _prepare_features(features):
    method_map = {'upi': 0, 'card': 1, 'netbanking': 2, 'wallet': 3, 'emi': 4}
    failure_map = {
        'temporary_failure': 0, 'insufficient_funds': 1,
        'card_expired': 2, 'authentication_failed': 3,
        'technical_error': 4, 'bank_declined': 5
    }

    return np.array([
        features.get('amount', 0),
        method_map.get(features.get('payment_method', 'upi'), 0),
        failure_map.get(features.get('failure_reason', 'temporary_failure'), 0),
        features.get('retry_count', 0),
        features.get('customer_successful_count', 0),
        features.get('customer_failed_count', 0),
        features.get('historical_success_rate', 0.5),
        features.get('account_age_days', 30),
    ])


def _rule_based_predict(features):
    prob = 0.5

    success_rate = features.get('historical_success_rate', 0.5)
    retry_count = features.get('retry_count', 0)
    amount = features.get('amount', 0)
    failure = features.get('failure_reason', '')
    account_age = features.get('account_age_days', 30)

    if success_rate >= 0.8:
        prob += 0.25
    elif success_rate >= 0.6:
        prob += 0.15
    elif success_rate < 0.3:
        prob -= 0.2

    if retry_count == 0:
        prob += 0.1
    elif retry_count >= 2:
        prob -= 0.25

    if failure == 'temporary_failure' and retry_count == 0:
        prob += 0.15
    elif failure == 'temporary_failure':
        prob += 0.05
    elif failure in ('card_expired', 'bank_declined'):
        prob -= 0.15

    if amount > 10000:
        prob -= 0.1

    if account_age > 365:
        prob += 0.05
    elif account_age < 30:
        prob -= 0.05

    return round(max(0.05, min(0.95, prob)), 4)


def get_feature_names():
    return [
        'amount', 'payment_method', 'failure_reason', 'retry_count',
        'customer_successful_count', 'customer_failed_count',
        'historical_success_rate', 'account_age_days'
    ]
