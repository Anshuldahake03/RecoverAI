import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.ml.predict import _rule_based_predict, get_feature_names


class TestRuleBasedPredict:
    def test_high_success_rate(self):
        features = {
            'amount': 1000, 'payment_method': 'upi',
            'failure_reason': 'temporary_failure', 'retry_count': 0,
            'customer_successful_count': 20, 'customer_failed_count': 2,
            'historical_success_rate': 0.9, 'account_age_days': 500
        }
        prob = _rule_based_predict(features)
        assert 0.7 <= prob <= 0.95

    def test_low_success_rate(self):
        features = {
            'amount': 5000, 'payment_method': 'card',
            'failure_reason': 'card_expired', 'retry_count': 3,
            'customer_successful_count': 2, 'customer_failed_count': 8,
            'historical_success_rate': 0.2, 'account_age_days': 15
        }
        prob = _rule_based_predict(features)
        assert 0.05 <= prob <= 0.4

    def test_max_retry(self):
        features = {
            'amount': 1000, 'payment_method': 'upi',
            'failure_reason': 'temporary_failure', 'retry_count': 3,
            'customer_successful_count': 10, 'customer_failed_count': 5,
            'historical_success_rate': 0.67, 'account_age_days': 200
        }
        prob = _rule_based_predict(features)
        assert prob < 0.5

    def test_feature_names(self):
        names = get_feature_names()
        assert len(names) == 8
        assert 'amount' in names
        assert 'retry_count' in names

    def test_bounds(self):
        features = {
            'amount': 100, 'payment_method': 'upi',
            'failure_reason': 'temporary_failure', 'retry_count': 0,
            'customer_successful_count': 0, 'customer_failed_count': 0,
            'historical_success_rate': 0.5, 'account_age_days': 30
        }
        prob = _rule_based_predict(features)
        assert 0.0 <= prob <= 1.0
