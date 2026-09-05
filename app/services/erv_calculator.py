import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ERVCalculator:
    COST_PER_AUTO_RETRY = 0.0
    COST_PER_WHATSAPP = 0.35
    COST_PER_SMS = 0.20
    COST_PER_EMAIL = 0.05
    COST_PER_VOICE_CALL = 4.50
    COST_PER_MANUAL_REVIEW = 15.00

    TIER_COSTS = {
        'AUTO_RETRY': COST_PER_AUTO_RETRY,
        'WHATSAPP': COST_PER_WHATSAPP,
        'SMS': COST_PER_SMS,
        'EMAIL': COST_PER_EMAIL,
        'VOICE_CALL': COST_PER_VOICE_CALL,
        'MANUAL_REVIEW': COST_PER_MANUAL_REVIEW,
        'NO_ACTION': 0.0
    }

    TIER_SUCCESS_RATES = {
        'AUTO_RETRY': 0.35,
        'WHATSAPP': 0.25,
        'SMS': 0.15,
        'EMAIL': 0.10,
        'VOICE_CALL': 0.40,
        'MANUAL_REVIEW': 0.50,
        'NO_ACTION': 0.0
    }

    @staticmethod
    def calculate_erv(amount, recovery_probability, tier, customer_ltv=None,
                      churn_risk=0.0):
        cost = ERVCalculator.TIER_COSTS.get(tier, 10.0)
        base_success = ERVCalculator.TIER_SUCCESS_RATES.get(tier, 0.1)

        adjusted_success = recovery_probability * base_success
        expected_recovery = amount * adjusted_success
        erv = expected_recovery - cost

        if customer_ltv:
            churn_penalty = churn_risk * customer_ltv * 0.1
            erv -= churn_penalty

        return {
            'erv': round(erv, 2),
            'expected_recovery': round(expected_recovery, 2),
            'action_cost': cost,
            'adjusted_success_rate': round(adjusted_success, 4),
            'amount': amount,
            'tier': tier,
            'churn_penalty': round(churn_risk * (customer_ltv or 0) * 0.1, 2)
        }

    @staticmethod
    def rank_tiers(amount, recovery_probability, customer_ltv=None, churn_risk=0.0):
        rankings = []
        for tier in ERVCalculator.TIER_COSTS:
            if tier == 'NO_ACTION':
                continue
            erv_result = ERVCalculator.calculate_erv(
                amount, recovery_probability, tier, customer_ltv, churn_risk
            )
            rankings.append(erv_result)

        rankings.sort(key=lambda x: x['erv'], reverse=True)
        return rankings

    @staticmethod
    def select_best_tier(amount, recovery_probability, customer_ltv=None,
                         churn_risk=0.0, min_erv=0.0):
        rankings = ERVCalculator.rank_tiers(
            amount, recovery_probability, customer_ltv, churn_risk
        )

        for ranking in rankings:
            if ranking['erv'] >= min_erv:
                return ranking

        return {
            'erv': 0,
            'expected_recovery': 0,
            'action_cost': 0,
            'adjusted_success_rate': 0,
            'amount': amount,
            'tier': 'NO_ACTION',
            'churn_penalty': 0,
            'reason': 'No tier exceeds minimum ERV threshold'
        }
