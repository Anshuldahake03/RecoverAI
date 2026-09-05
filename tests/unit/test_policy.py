import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.policy_service import validate_policy


class MockTransaction:
    def __init__(self, status='FAILED', retry_count=0, amount=1000):
        self.status = status
        self.retry_count = retry_count
        self.amount = amount


class MockRecommendation:
    def __init__(self, action='RETRY', confidence=0.8, requires_approval=False):
        self.action = action
        self.confidence = confidence
        self.requires_approval = requires_approval


class TestPolicyEngine:
    def test_recovered_blocked(self):
        txn = MockTransaction(status='RECOVERED')
        rec = MockRecommendation()
        result = validate_policy(txn, rec)
        assert result['allowed'] is False

    def test_retry_limit(self):
        txn = MockTransaction(retry_count=5)
        rec = MockRecommendation()
        result = validate_policy(txn, rec)
        assert result['allowed'] is False

    def test_high_amount_approval(self):
        txn = MockTransaction(amount=15000)
        rec = MockRecommendation(action='RETRY', confidence=0.8)
        result = validate_policy(txn, rec)
        assert result['requires_approval'] is True

    def test_valid_auto(self):
        txn = MockTransaction(amount=5000, retry_count=0)
        rec = MockRecommendation(action='RETRY', confidence=0.8)
        result = validate_policy(txn, rec)
        assert result['allowed'] is True
        assert result['requires_approval'] is False

    def test_escalate_needs_approval(self):
        txn = MockTransaction(amount=5000)
        rec = MockRecommendation(action='ESCALATE')
        result = validate_policy(txn, rec)
        assert result['requires_approval'] is True

    def test_duplicate_action_blocked(self):
        txn = MockTransaction()
        rec = MockRecommendation()
        existing = [MockRecommendation()]
        existing[0].status = 'PENDING'
        result = validate_policy(txn, rec, existing)
        assert result['allowed'] is False

    def test_invalid_action_blocked(self):
        txn = MockTransaction()
        rec = MockRecommendation(action='INVALID_ACTION')
        result = validate_policy(txn, rec)
        assert result['allowed'] is False
