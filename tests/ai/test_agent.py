import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.ai.agent import get_fallback_recommendation


class TestFallbackAgent:
    def test_high_probability_retry(self):
        context = {
            'recovery_probability': 0.85, 'retry_count': 0,
            'amount': 2000, 'failure_reason': 'temporary_failure',
            'previous_success_rate': 0.9
        }
        result = get_fallback_recommendation(context)
        assert result['action'] == 'RETRY'
        assert result['decision_source'] == 'FALLBACK_RULE'

    def test_max_retry_no_action(self):
        context = {
            'recovery_probability': 0.7, 'retry_count': 3,
            'amount': 2000, 'failure_reason': 'temporary_failure',
            'previous_success_rate': 0.8
        }
        result = get_fallback_recommendation(context)
        assert result['action'] == 'NO_ACTION'

    def test_high_value_escalate(self):
        context = {
            'recovery_probability': 0.6, 'retry_count': 0,
            'amount': 15000, 'failure_reason': 'temporary_failure',
            'previous_success_rate': 0.7
        }
        result = get_fallback_recommendation(context)
        assert result['action'] == 'ESCALATE'
        assert result['requires_human_approval'] is True

    def test_medium_prob_payment_link(self):
        context = {
            'recovery_probability': 0.55, 'retry_count': 0,
            'amount': 3000, 'failure_reason': 'technical_error',
            'previous_success_rate': 0.5
        }
        result = get_fallback_recommendation(context)
        assert result['action'] == 'SEND_PAYMENT_LINK'

    def test_low_prob_escalate(self):
        context = {
            'recovery_probability': 0.15, 'retry_count': 1,
            'amount': 5000, 'failure_reason': 'bank_declined',
            'previous_success_rate': 0.3
        }
        result = get_fallback_recommendation(context)
        assert result['action'] == 'ESCALATE'
